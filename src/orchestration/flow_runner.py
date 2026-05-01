from __future__ import annotations

import time
from typing import Any, Callable

from src.config_loader import get_project_config
from src.opencode.client import OpenCodeClient
from src.orchestration.prompt_builder import build_initial_prompt, build_retry_prompt
from src.orchestration.report_writer import write_json_report, write_markdown_report
from src.quality.quality_gate import run_quality_gate
from src.reviewer.crew_reviewer import review_change


ProgressFn = Callable[[str], None]


def _emit(progress: ProgressFn | None, message: str) -> None:
    if progress:
        progress(message)


def _session_id(payload: dict[str, Any]) -> str:
    candidates = [
        payload.get("id"),
        payload.get("session_id"),
        payload.get("sessionID"),
        payload.get("session", {}).get("id") if isinstance(payload.get("session"), dict) else None,
        payload.get("data", {}).get("id") if isinstance(payload.get("data"), dict) else None,
    ]
    for value in candidates:
        if value:
            return str(value)
    raise ValueError(f"could not find session id in OpenCode response: {payload}")


def _disabled_review() -> dict[str, Any]:
    return {
        "passed": True,
        "score": 100,
        "blocking_issues": [],
        "non_blocking_issues": [],
        "retry_instruction": "",
        "raw": "reviewer disabled",
    }


def _write_reports(report: dict[str, Any]) -> dict[str, Any]:
    write_markdown_report(report)
    write_json_report(report)
    return report


def run_dev_task(
    project_id: str,
    task_text: str,
    max_iterations: int | None = None,
    progress: ProgressFn | None = None,
) -> dict:
    project_config = get_project_config(project_id)
    limit = int(max_iterations or project_config.get("max_iterations", 3))
    client = OpenCodeClient.from_project_config(project_config)

    report: dict[str, Any] = {
        "project_id": project_id,
        "task": task_text,
        "session_id": "",
        "passed": False,
        "iterations_used": 0,
        "max_iterations": limit,
        "quality": {},
        "review": {},
        "iterations": [],
    }

    try:
        health = client.health()
        _emit(progress, f"OpenCode health: ok {health}")
        current_path = client.current_path()
        _emit(progress, f"OpenCode current path: {current_path}")
        vcs = client.vcs()
        _emit(progress, f"OpenCode vcs: {vcs}")

        session = client.create_session(f"AI dev task: {task_text[:80]}")
        session_id = _session_id(session)
        report["session_id"] = session_id
        _emit(progress, f"session_id: {session_id}")

        last_quality: dict[str, Any] = {}
        last_review: dict[str, Any] = {}

        for iteration in range(1, limit + 1):
            _emit(progress, f"iteration {iteration}/{limit}: sending task to OpenCode")
            prompt = (
                build_initial_prompt(task_text, project_config)
                if iteration == 1
                else build_retry_prompt(task_text, last_quality, last_review, iteration)
            )

            send_result = client.send_message(session_id, prompt, project_config.get("opencode_agent", "build"))
            _emit(progress, f"iteration {iteration}/{limit}: message sent")
            time.sleep(float(project_config.get("post_message_wait_seconds", 1)))

            try:
                opencode_diff = client.get_diff(session_id)
            except Exception as exc:
                opencode_diff = {"error": str(exc)}

            quality = run_quality_gate(project_config)
            _emit(progress, f"quality gate: {'PASS' if quality.get('passed') else 'FAIL'}")

            review = (
                review_change(task_text, quality)
                if project_config.get("reviewer_enabled", True)
                else _disabled_review()
            )
            _emit(progress, f"reviewer: {'PASS' if review.get('passed') else 'FAIL'}")

            iteration_passed = bool(quality.get("passed") and review.get("passed"))
            iteration_report = {
                "iteration": iteration,
                "send_result": send_result,
                "opencode_diff": opencode_diff,
                "quality_passed": quality.get("passed"),
                "review_passed": review.get("passed"),
                "passed": iteration_passed,
            }
            report["iterations"].append(iteration_report)
            report["iterations_used"] = iteration
            report["quality"] = quality
            report["review"] = review

            last_quality = quality
            last_review = review

            if iteration_passed:
                report["passed"] = True
                _emit(progress, "task passed")
                break

            if iteration < limit:
                _emit(progress, f"iteration {iteration}/{limit}: will retry with failure context")

        if not report["passed"]:
            _emit(progress, "task failed after max iterations")
        return _write_reports(report)
    except Exception as exc:
        report["error"] = str(exc)
        report["review"] = report.get("review") or {
            "passed": False,
            "score": 0,
            "blocking_issues": [str(exc)],
            "non_blocking_issues": [],
            "retry_instruction": "Fix the OpenCode or orchestration error and rerun the task.",
            "raw": "flow exception",
        }
        _emit(progress, f"flow failed: {exc}")
        return _write_reports(report)

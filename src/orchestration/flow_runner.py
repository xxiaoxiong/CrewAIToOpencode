from __future__ import annotations

import time
from typing import Any, Callable

from src.agents.architect_agent import build_architect_plan
from src.agents.reporter_agent import summarize_delivery
from src.agents.tester_agent import analyze_test_failure
from src.config_loader import get_effective_pipeline, get_project_config
from src.opencode.client import OpenCodeClient
from src.opencode.multi_agent_runner import build as opencode_build
from src.opencode.multi_agent_runner import explore as opencode_explore
from src.opencode.multi_agent_runner import plan as opencode_plan_task
from src.opencode.multi_agent_runner import repair as opencode_repair
from src.opencode.multi_agent_runner import validate as opencode_validate
from src.orchestration.context_compactor import prompt_summary
from src.orchestration.prompt_builder import build_initial_prompt, build_retry_prompt
from src.orchestration.report_writer import write_json_report, write_markdown_report
from src.orchestration.task_context import TaskContext
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


def _infer_failed_stage(report: dict[str, Any]) -> str:
    if report.get("failed_stage"):
        return str(report["failed_stage"])
    if report.get("error_stage"):
        return str(report["error_stage"])
    if report.get("error"):
        return "build"
    quality = report.get("quality", {}) or {}
    validator = report.get("validator", {}) or {}
    reviewer = report.get("reviewer", report.get("review", {})) or {}
    if quality and quality.get("passed") is False:
        return "quality_gate"
    if validator and validator.get("passed") is False:
        return "validator"
    if reviewer and reviewer.get("passed") is False:
        return "reviewer"
    return "build"


def _prompt_limit(project_config: dict[str, Any], key: str, default: int) -> int:
    configured = project_config.get("prompt_limits", {}) or {}
    return int(configured.get(key, default))


def _assert_prompt_size(prompt: str, limit: int, stage: str) -> None:
    if len(prompt) > limit:
        raise ValueError(f"{stage} prompt is {len(prompt)} chars, above limit {limit}; compact context before sending.")


def _crewai_enabled(project_config: dict[str, Any], key: str | None = None) -> bool:
    crewai_config = project_config.get("crewai", {}) or {}
    if not crewai_config.get("enabled", False):
        return False
    if key is None:
        return True
    return bool(crewai_config.get(key, True))


def _pipeline_for_config(project_config: dict[str, Any], mode: str | None) -> dict[str, Any]:
    if mode or "task_pipeline" in project_config:
        return get_effective_pipeline(project_config, mode)
    if (project_config.get("crewai", {}) or {}).get("enabled"):
        return {
            "explore_enabled": False,
            "architect_enabled": True,
            "opencode_plan_enabled": False,
            "build_enabled": True,
            "tester_enabled": True,
            "validator_enabled": True,
            "reviewer_enabled": True,
            "reporter_enabled": True,
            "max_iterations": project_config.get("max_iterations", 3),
            "mode": "v0.2",
        }
    return {
        "explore_enabled": False,
        "architect_enabled": False,
        "opencode_plan_enabled": False,
        "build_enabled": True,
        "tester_enabled": False,
        "validator_enabled": True,
        "reviewer_enabled": True,
        "reporter_enabled": False,
        "max_iterations": project_config.get("max_iterations", 3),
        "mode": "legacy",
    }


def run_dev_task(
    project_id: str,
    task_text: str,
    max_iterations: int | None = None,
    mode: str | None = None,
    progress: ProgressFn | None = None,
) -> dict:
    project_config = get_project_config(project_id)
    pipeline = _pipeline_for_config(project_config, mode)
    limit = int(max_iterations or pipeline.get("max_iterations") or project_config.get("max_iterations", 3))
    client = OpenCodeClient.from_project_config(project_config)
    context = TaskContext(project_id=project_id, task_text=task_text, mode=str(pipeline.get("mode", mode or "custom")))

    report: dict[str, Any] = {
        "project_id": project_id,
        "task": task_text,
        "mode": context.mode,
        "pipeline": pipeline,
        "session_id": "",
        "passed": False,
        "iterations_used": 0,
        "max_iterations": limit,
        "explore": {},
        "architect_plan": {},
        "opencode_plan": {},
        "build": {},
        "quality": {},
        "tester": {},
        "validator": {},
        "reviewer": {},
        "review": {},
        "plan": {},
        "reporter": {},
        "retry_history": [],
        "iterations": [],
        "failed_stage": "",
        "prompt_metrics": {},
    }

    current_stage = "startup"
    try:
        current_stage = "explore"
        health = client.health()
        _emit(progress, f"OpenCode health: ok {health}")
        current_path = client.current_path()
        _emit(progress, f"OpenCode current path: {current_path}")
        vcs = client.vcs()
        _emit(progress, f"OpenCode vcs: {vcs}")

        session = client.create_session(f"AI dev task: {task_text[:80]}")
        session_id = _session_id(session)
        context.session_id = session_id
        report["session_id"] = session_id
        _emit(progress, f"session_id: {session_id}")

        explore_result: dict[str, Any] = {}
        if pipeline.get("explore_enabled"):
            current_stage = "explore"
            explore_result = opencode_explore(session_id, task_text, project_config)
            context.explore_result = explore_result
            report["explore"] = explore_result
            _emit(progress, "opencode explore: done")

        architect_plan: dict[str, Any] = {}
        if pipeline.get("architect_enabled"):
            current_stage = "architect"
            repo_context = {
                "health": health,
                "path": current_path,
                "vcs": vcs,
                "explore": explore_result,
            }
            architect_plan = build_architect_plan(task_text, project_config, repo_context)
            context.architect_plan = architect_plan
            report["architect_plan"] = architect_plan
            report["plan"] = architect_plan
            _emit(progress, f"architect: {'PASS' if architect_plan.get('passed') else 'FALLBACK/FAIL'}")

        opencode_plan_result: dict[str, Any] = {}
        if pipeline.get("opencode_plan_enabled"):
            current_stage = "opencode_plan"
            opencode_plan_result = opencode_plan_task(session_id, task_text, explore_result, architect_plan, project_config)
            context.opencode_plan = opencode_plan_result
            report["opencode_plan"] = opencode_plan_result
            report["prompt_metrics"]["plan_prompt_chars"] = opencode_plan_result.get("prompt_chars", 0)
            _emit(progress, "opencode plan: done")

        last_quality: dict[str, Any] = {}
        last_review: dict[str, Any] = {}
        last_tester: dict[str, Any] = {}
        last_validator: dict[str, Any] = {}

        for iteration in range(1, limit + 1):
            context.iteration = iteration
            _emit(progress, f"iteration {iteration}/{limit}: sending task to OpenCode")
            if iteration == 1:
                current_stage = "build"
                prompt = build_initial_prompt(
                    task_text,
                    project_config,
                    architect_plan if architect_plan else None,
                    explore_result=explore_result,
                    opencode_plan=opencode_plan_result,
                )
                report["prompt_metrics"]["build_prompt_chars"] = len(prompt)
                _emit(progress, f"build prompt chars: {len(prompt)}")
                _assert_prompt_size(prompt, _prompt_limit(project_config, "build_max_chars", 12000), "build")
                send_result = (
                    opencode_build(session_id, prompt, project_config)
                    if pipeline.get("build_enabled", True)
                    else {"skipped": True, "reason": "build stage disabled"}
                )
                report["build"] = send_result
                context.build_result = send_result
                action = "build"
            else:
                current_stage = "build"
                prompt = build_retry_prompt(task_text, last_quality, last_review, iteration, last_tester, last_validator)
                report["prompt_metrics"]["retry_prompt_chars"] = len(prompt)
                _emit(progress, f"retry prompt chars: {len(prompt)}")
                _assert_prompt_size(prompt, _prompt_limit(project_config, "retry_max_chars", 8000), "retry")
                send_result = opencode_repair(session_id, prompt, project_config)
                report["retry_history"].append(
                    {
                        "iteration": iteration,
                        "prompt_summary": prompt_summary(prompt),
                        "prompt_chars": len(prompt),
                        "result": send_result,
                    }
                )
                action = "repair"
            _emit(progress, f"iteration {iteration}/{limit}: message sent")
            time.sleep(float(project_config.get("post_message_wait_seconds", 1)))

            try:
                opencode_diff = client.get_diff(session_id)
            except Exception as exc:
                opencode_diff = {"error": str(exc)}

            current_stage = "quality_gate"
            quality = run_quality_gate(project_config, task_text)
            context.quality_result = quality
            _emit(progress, f"quality gate: {'PASS' if quality.get('passed') else 'FAIL'}")

            tester = (
                analyze_test_failure(task_text, quality, project_config)
                if pipeline.get("tester_enabled") and quality.get("test", {}).get("passed") is False
                else {}
            )
            context.tester_result = tester
            if tester:
                _emit(progress, f"tester analyst: {'PASS' if tester.get('passed') else 'ANALYZED'}")

            current_stage = "validator"
            validator = (
                opencode_validate(session_id, task_text, quality, project_config)
                if pipeline.get("validator_enabled", True)
                else {"passed": True, "summary": "validator disabled", "blocking_issues": []}
            )
            context.validator_result = validator
            _emit(progress, f"validator: {'PASS' if validator.get('passed') else 'FAIL'}")

            current_stage = "reviewer"
            review = (
                (
                    review_change(task_text, quality, project_config)
                    if _crewai_enabled(project_config, "reviewer_enabled")
                    else review_change(task_text, quality)
                )
                if project_config.get("reviewer_enabled", True) and pipeline.get("reviewer_enabled", True)
                else _disabled_review()
            )
            context.reviewer_result = review
            _emit(progress, f"reviewer: {'PASS' if review.get('passed') else 'FAIL'}")

            iteration_passed = bool(quality.get("passed") and validator.get("passed") and review.get("passed"))
            context.passed = iteration_passed
            iteration_report = {
                "iteration": iteration,
                "action": action,
                "send_result": send_result,
                "opencode_diff": opencode_diff,
                "quality_passed": quality.get("passed"),
                "tester": tester,
                "validator": validator,
                "review_passed": review.get("passed"),
                "passed": iteration_passed,
            }
            report["iterations"].append(iteration_report)
            report["iterations_used"] = iteration
            report["quality"] = quality
            report["tester"] = tester
            report["validator"] = validator
            report["reviewer"] = review
            report["review"] = review

            last_quality = quality
            last_tester = tester
            last_validator = validator
            last_review = review

            if iteration_passed:
                report["passed"] = True
                _emit(progress, "task passed")
                break

            if iteration < limit:
                _emit(progress, f"iteration {iteration}/{limit}: will retry with failure context")

        if not report["passed"]:
            report["failed_stage"] = _infer_failed_stage(report)
            _emit(progress, "task failed after max iterations")
        if pipeline.get("reporter_enabled"):
            current_stage = "reporter"
            reporter = summarize_delivery(report, project_config)
            context.reporter_result = reporter
            report["reporter"] = reporter
            _emit(progress, f"reporter: {'PASS' if reporter.get('passed') else 'FALLBACK/FAIL'}")
        return _write_reports(report)
    except Exception as exc:
        report["error"] = str(exc)
        report["failed_stage"] = current_stage
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

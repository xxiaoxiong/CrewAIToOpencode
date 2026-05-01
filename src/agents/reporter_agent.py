from __future__ import annotations

import json
import os
from typing import Any

from src.agents.json_utils import coerce_string_list, parse_json_object
from src.agents.llm_factory import create_llm
from src.orchestration.context_compactor import sanitize_stage_payload


def _fallback_report(report: dict[str, Any], reason: str = "") -> dict[str, Any]:
    quality = report.get("quality", {}) or {}
    return {
        "passed": bool(report.get("passed")),
        "summary": "Task completed successfully." if report.get("passed") else "Task did not pass validation.",
        "changed_files": coerce_string_list(quality.get("changed_files", [])),
        "validation_summary": "Quality gate passed." if quality.get("passed") else "Quality gate failed.",
        "follow_up": [],
        "raw": reason or "reporter fallback",
    }


def _build_prompt(report: dict[str, Any]) -> str:
    quality = report.get("quality", {}) or {}
    payload = {
        "task": report.get("task", ""),
        "task_contract": report.get("task_contract", {}),
        "repo_summary": report.get("repo_summary", {}),
        "passed": report.get("passed"),
        "iterations_used": report.get("iterations_used"),
        "quality": {
            "passed": quality.get("passed"),
            "changed_files": quality.get("changed_files", []),
            "test": quality.get("test", {}),
            "lint": quality.get("lint", {}),
            "file_policy": quality.get("file_policy", {}),
            "bad_patterns": quality.get("bad_patterns", {}),
        },
        "validator": report.get("validator", {}),
        "review": report.get("review", {}),
        "tester": report.get("tester", {}),
    }
    return (
        "You are a Reporter Agent. Summarize the completed development task. "
        "Return strict JSON only with keys: passed, summary, changed_files, validation_summary, follow_up.\n"
        f"Input:\n{json.dumps(sanitize_stage_payload(payload), ensure_ascii=False, indent=2)}"
    )


def _run_crewai(prompt: str, project_config: dict[str, Any]) -> str:
    from crewai import Agent, Crew, Task

    llm = create_llm(project_config)
    agent = Agent(
        role="Delivery reporter",
        goal="Summarize accepted code changes and validation results.",
        backstory="You write concise engineering delivery summaries in strict JSON.",
        verbose=False,
        llm=llm,
    )
    task = Task(description=prompt, expected_output="Strict JSON report summary.", agent=agent)
    crew = Crew(agents=[agent], tasks=[task], verbose=False)
    return str(crew.kickoff())


def summarize_delivery(report: dict[str, Any], project_config: dict[str, Any]) -> dict[str, Any]:
    if os.getenv("CREWAI_DISABLE_LLM", "").lower() in {"1", "true", "yes"}:
        return _fallback_report(report, "CREWAI_DISABLE_LLM is set")

    try:
        raw = _run_crewai(_build_prompt(report), project_config)
    except Exception as exc:
        return _fallback_report(report, f"Reporter Agent fallback: {exc}")

    result = parse_json_object(raw, _fallback_report(report, "invalid reporter JSON"))
    result["passed"] = bool(result.get("passed", report.get("passed", False)))
    result["changed_files"] = coerce_string_list(result.get("changed_files", []))
    result["follow_up"] = coerce_string_list(result.get("follow_up", []))
    return result

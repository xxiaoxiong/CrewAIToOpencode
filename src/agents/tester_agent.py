from __future__ import annotations

import json
import os
from typing import Any

from src.agents.json_utils import parse_json_object
from src.agents.llm_factory import create_llm


def _test_failed(quality_result: dict[str, Any]) -> bool:
    test = quality_result.get("test", {}) or {}
    return bool(test.get("enabled", True)) and test.get("passed") is False


def _fallback_analysis(quality_result: dict[str, Any], reason: str = "") -> dict[str, Any]:
    test = quality_result.get("test", {}) or {}
    stderr = str(test.get("stderr", "") or "")
    stdout = str(test.get("stdout", "") or "")
    combined = f"{stdout}\n{stderr}".lower()
    failure_type = "unclear"
    if "modulenotfounderror" in combined or "no module named" in combined:
        failure_type = "dependency_issue"
    elif "command not found" in combined or "not recognized" in combined:
        failure_type = "env_issue"
    elif combined.strip():
        failure_type = "code_issue"

    return {
        "mode": "fallback",
        "passed": False,
        "failure_type": failure_type,
        "root_cause_summary": "Deterministic test analysis fallback. Inspect stdout/stderr for the exact failure.",
        "retry_instruction": "Fix the failing test cause without weakening or deleting tests, then rerun validation.",
        "raw": reason or "tester fallback",
    }


def _no_failure_result() -> dict[str, Any]:
    return {
        "mode": "disabled",
        "passed": True,
        "failure_type": "",
        "root_cause_summary": "",
        "retry_instruction": "",
        "raw": "tests passed or disabled",
    }


def _build_prompt(task_text: str, quality_result: dict[str, Any]) -> str:
    test = quality_result.get("test", {}) or {}
    payload = {
        "task": task_text,
        "changed_files": quality_result.get("changed_files", []),
        "test": {
            "cmd": test.get("cmd", ""),
            "stdout": str(test.get("stdout", ""))[-8000:],
            "stderr": str(test.get("stderr", ""))[-8000:],
            "returncode": test.get("returncode"),
        },
    }
    return (
        "You are a Tester Analyst Agent. Analyze the failing test and produce strict JSON only with keys: "
        "passed, failure_type, root_cause_summary, retry_instruction. "
        "failure_type must be one of code_issue, env_issue, dependency_issue, unclear.\n"
        f"Input:\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )


def _run_crewai(prompt: str, project_config: dict[str, Any]) -> str:
    from crewai import Agent, Crew, Task

    llm = create_llm(project_config)
    agent = Agent(
        role="Test failure analyst",
        goal="Classify test failures and produce actionable retry guidance.",
        backstory="You read command output carefully and return strict JSON.",
        verbose=False,
        llm=llm,
    )
    task = Task(description=prompt, expected_output="Strict JSON test analysis.", agent=agent)
    crew = Crew(agents=[agent], tasks=[task], verbose=False)
    return str(crew.kickoff())


def analyze_test_failure(
    task_text: str,
    quality_result: dict[str, Any],
    project_config: dict[str, Any],
) -> dict[str, Any]:
    if not _test_failed(quality_result):
        return _no_failure_result()
    if os.getenv("CREWAI_DISABLE_LLM", "").lower() in {"1", "true", "yes"}:
        return _fallback_analysis(quality_result, "CREWAI_DISABLE_LLM is set")

    try:
        raw = _run_crewai(_build_prompt(task_text, quality_result), project_config)
    except Exception as exc:
        return _fallback_analysis(quality_result, f"Tester Analyst fallback: {exc}")

    result = parse_json_object(raw, _fallback_analysis(quality_result, "invalid tester JSON"))
    result["mode"] = "llm"
    result["passed"] = bool(result.get("passed", False))
    result["failure_type"] = str(result.get("failure_type", "unclear") or "unclear")
    result["root_cause_summary"] = str(result.get("root_cause_summary", ""))
    result["retry_instruction"] = str(result.get("retry_instruction", ""))
    return result

from __future__ import annotations

import json
from typing import Any

from src.agents.json_utils import coerce_string_list, parse_json_object
from src.agents.llm_factory import create_llm
from src.orchestration.context_compactor import sanitize_stage_payload


def build_semantic_review_prompt(task_text: str | dict[str, Any], quality_result: dict[str, Any]) -> str:
    test = quality_result.get("test", {}) or {}
    lint = quality_result.get("lint", {}) or {}
    payload = {
        "task_contract": sanitize_stage_payload(task_text) if isinstance(task_text, dict) else {"goal": task_text},
        "changed_files": quality_result.get("changed_files", []),
        "git_diff_stat": quality_result.get("git_diff_stat", ""),
        "diff_excerpt": str(quality_result.get("diff", ""))[-12000:],
        "test": {
            "enabled": test.get("enabled"),
            "passed": test.get("passed"),
            "cmd": test.get("cmd", ""),
            "stdout_tail": str(test.get("stdout", ""))[-1200:],
            "stderr_tail": str(test.get("stderr", ""))[-1200:],
        },
        "lint": {
            "enabled": lint.get("enabled"),
            "passed": lint.get("passed"),
            "cmd": lint.get("cmd", ""),
            "stdout_tail": str(lint.get("stdout", ""))[-800:],
            "stderr_tail": str(lint.get("stderr", ""))[-800:],
        },
        "file_policy": quality_result.get("file_policy", {}),
        "bad_patterns": quality_result.get("bad_patterns", {}),
    }
    return (
        "You are a semantic code reviewer. Deterministic quality gates have already run. "
        "Return strict JSON only with keys: passed, score, blocking_issues, non_blocking_issues, retry_instruction. "
        "Focus on task fit, over-editing, obvious bugs, and missing validation.\n"
        f"Input:\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )


def run_semantic_review(task_text: str | dict[str, Any], quality_result: dict[str, Any], project_config: dict[str, Any]) -> dict[str, Any]:
    from crewai import Agent, Crew, Task

    llm = create_llm(project_config)
    agent = Agent(
        role="Senior code reviewer",
        goal="Find semantic issues in a code diff and return strict JSON.",
        backstory="You supplement deterministic gates with careful semantic review.",
        verbose=False,
        llm=llm,
    )
    task = Task(
        description=build_semantic_review_prompt(task_text, quality_result),
        expected_output="Strict JSON semantic review.",
        agent=agent,
    )
    crew = Crew(agents=[agent], tasks=[task], verbose=False)
    raw = str(crew.kickoff())
    result = parse_json_object(
        raw,
        {
            "mode": "fallback",
            "passed": False,
            "score": 0,
            "blocking_issues": ["CrewAI reviewer output was not valid JSON."],
            "non_blocking_issues": [],
            "retry_instruction": "Inspect the change manually or rerun semantic review.",
            "raw": raw,
        },
    )
    result["mode"] = "llm"
    result["passed"] = bool(result.get("passed", False))
    result["score"] = int(result.get("score", 0) or 0)
    result["blocking_issues"] = coerce_string_list(result.get("blocking_issues", []))
    result["non_blocking_issues"] = coerce_string_list(result.get("non_blocking_issues", []))
    result["retry_instruction"] = str(result.get("retry_instruction", ""))
    return result

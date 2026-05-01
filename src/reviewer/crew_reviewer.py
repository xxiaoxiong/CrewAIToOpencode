from __future__ import annotations

import json
import os
from typing import Any

from src.agents.reviewer_agent import run_semantic_review
from src.orchestration.context_compactor import sanitize_stage_payload


def _default_result(raw: str = "") -> dict[str, Any]:
    return {
        "passed": False,
        "score": 0,
        "blocking_issues": [],
        "non_blocking_issues": [],
        "retry_instruction": "",
        "raw": raw,
    }


def _coerce_review(raw: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            result = _default_result(raw)
            result.update(parsed)
            result["passed"] = bool(result.get("passed"))
            result["score"] = int(result.get("score", 0))
            result.setdefault("blocking_issues", [])
            result.setdefault("non_blocking_issues", [])
            result.setdefault("retry_instruction", "")
            result["raw"] = raw
            return result
    except Exception:
        pass

    lowered = raw.lower()
    result = _default_result(raw)
    if '"passed": true' in lowered or "passed true" in lowered or "passed: true" in lowered:
        result["passed"] = True
        result["score"] = 80
    else:
        result["blocking_issues"] = ["Reviewer output was not valid JSON."]
        result["retry_instruction"] = "Please fix the change and provide reviewable output."
    return result


def _build_review_prompt(task_text: str | dict[str, Any], quality_result: dict) -> str:
    payload = {
        "task_contract": sanitize_stage_payload(task_text) if isinstance(task_text, dict) else {"goal": task_text},
        "changed_files": quality_result.get("changed_files", []),
        "quality_passed": quality_result.get("passed"),
        "git_diff_stat": quality_result.get("git_diff_stat", ""),
        "diff": quality_result.get("diff", "")[-16000:],
        "test": quality_result.get("test", {}),
        "lint": quality_result.get("lint", {}),
        "file_policy": quality_result.get("file_policy", {}),
        "bad_patterns": quality_result.get("bad_patterns", {}),
    }
    return f"""你是严格的代码审查 Reviewer Agent。

请审查以下变更是否真正解决原始任务，是否过度修改，是否有明显 bug 或安全风险，是否需要返工。

只输出 JSON，不要 Markdown。JSON 格式必须是：
{{
  "passed": true,
  "score": 90,
  "blocking_issues": [],
  "non_blocking_issues": [],
  "retry_instruction": "",
  "raw": ""
}}

审查输入：
{json.dumps(payload, ensure_ascii=False, indent=2)}
"""


def _review_with_crewai(prompt: str) -> str | None:
    try:
        from crewai import Agent, Crew, Task
    except Exception:
        return None

    try:
        reviewer = Agent(
            role="Senior code reviewer",
            goal="Review code changes and return strict JSON.",
            backstory="You are careful, concise, and block unsafe or incomplete code changes.",
            verbose=False,
        )
        task = Task(description=prompt, expected_output="Strict JSON review result.", agent=reviewer)
        crew = Crew(agents=[reviewer], tasks=[task], verbose=False)
        output = crew.kickoff()
        return str(output)
    except Exception as exc:
        return json.dumps(
            {
                "passed": False,
                "score": 0,
                "blocking_issues": [f"CrewAI reviewer failed: {exc}"],
                "non_blocking_issues": [],
                "retry_instruction": "Fix reviewer/runtime configuration or inspect the change manually.",
            },
            ensure_ascii=False,
        )


def _heuristic_review(quality_result: dict) -> dict[str, Any]:
    result = _default_result("heuristic reviewer fallback")
    blocking: list[str] = []

    if not quality_result.get("passed"):
        blocking.append("Quality gate did not pass.")
    if not quality_result.get("changed_files"):
        blocking.append("No changed files were detected.")
    if quality_result.get("file_policy", {}).get("passed") is False:
        blocking.append("File policy violations were detected.")
    if quality_result.get("bad_patterns", {}).get("passed") is False:
        blocking.append("Dangerous patterns were detected in the diff.")
    if quality_result.get("test", {}).get("passed") is False:
        blocking.append("Test command failed.")
    if quality_result.get("lint", {}).get("passed") is False:
        blocking.append("Lint command failed.")

    result["blocking_issues"] = blocking
    result["passed"] = not blocking
    result["score"] = 85 if result["passed"] else 40
    result["retry_instruction"] = "" if result["passed"] else "Fix the blocking quality or review issues above."
    return result


def _hard_fail_reasons(quality_result: dict) -> list[str]:
    reasons: list[str] = []
    if quality_result.get("file_policy", {}).get("passed") is False:
        reasons.append("File policy violations cannot be overridden by CrewAI.")
    if quality_result.get("bad_patterns", {}).get("passed") is False:
        reasons.append("Dangerous pattern hits cannot be overridden by CrewAI.")
    if quality_result.get("test", {}).get("passed") is False:
        reasons.append("Test failures cannot be overridden by CrewAI.")
    return reasons


def _merge_semantic_review(base: dict[str, Any], semantic: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    blocking = list(result.get("blocking_issues", []) or [])
    non_blocking = list(result.get("non_blocking_issues", []) or [])
    blocking.extend(str(item) for item in semantic.get("blocking_issues", []) or [])
    non_blocking.extend(str(item) for item in semantic.get("non_blocking_issues", []) or [])
    result["blocking_issues"] = blocking
    result["non_blocking_issues"] = non_blocking
    result["passed"] = bool(result.get("passed")) and bool(semantic.get("passed"))
    result["score"] = min(int(result.get("score", 0)), int(semantic.get("score", 0) or 0))
    if semantic.get("retry_instruction"):
        result["retry_instruction"] = semantic["retry_instruction"]
    result["raw"] = semantic.get("raw", result.get("raw", ""))
    return result


def review_change(task_text: str | dict[str, Any], quality_result: dict, project_config: dict | None = None) -> dict[str, Any]:
    heuristic = _heuristic_review(quality_result)
    hard_fail_reasons = _hard_fail_reasons(quality_result)
    if hard_fail_reasons:
        heuristic["blocking_issues"] = list(dict.fromkeys([*heuristic.get("blocking_issues", []), *hard_fail_reasons]))
        heuristic["passed"] = False
        heuristic["score"] = 0
        return heuristic

    if os.getenv("REVIEWER_DISABLE_LLM", "").lower() in {"1", "true", "yes"}:
        return heuristic

    crewai_config = (project_config or {}).get("crewai", {}) or {}
    if not crewai_config.get("enabled") or not crewai_config.get("reviewer_enabled", True):
        return heuristic

    try:
        semantic = run_semantic_review(task_text, quality_result, project_config or {})
    except Exception as exc:
        semantic = {
            "passed": True,
            "score": heuristic.get("score", 85),
            "blocking_issues": [],
            "non_blocking_issues": [f"CrewAI semantic reviewer unavailable: {exc}"],
            "retry_instruction": "",
            "raw": "semantic reviewer fallback",
        }
    return _merge_semantic_review(heuristic, semantic)

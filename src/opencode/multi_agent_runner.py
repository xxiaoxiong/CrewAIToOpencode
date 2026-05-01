from __future__ import annotations

import json
from typing import Any

from src.opencode.client import OpenCodeClient
from src.orchestration.context_compactor import (
    compact_build_result,
    compact_explore_result,
    compact_plan_result,
    compact_validator_result,
    repo_fact_summary_from_explore,
    sanitize_stage_payload,
)
from src.orchestration.task_contract import build_task_contract, compact_task_contract


def _agent(project_config: dict[str, Any], key: str, fallback: str) -> str:
    return str((project_config.get("opencode_agents", {}) or {}).get(key) or fallback)


def _client(project_config: dict[str, Any]) -> OpenCodeClient:
    return OpenCodeClient.from_project_config(project_config)


def _timeout(project_config: dict[str, Any], stage: str) -> int:
    configured = project_config.get("opencode_timeouts", {}) or {}
    return int(configured.get(stage, configured.get("default", 600)))


def _prompt_limit(project_config: dict[str, Any], key: str, default: int) -> int:
    configured = project_config.get("prompt_limits", {}) or {}
    return int(configured.get(key, default))


def _ensure_prompt_within_limit(prompt: str, limit: int, stage: str) -> None:
    if len(prompt) > limit:
        raise ValueError(f"{stage} prompt is {len(prompt)} chars, above limit {limit}; compact context before sending.")


def explore(session_id: str, task_text: str, project_config: dict[str, Any]) -> dict[str, Any]:
    prompt = f"""You are the OpenCode explore agent for a personal local workflow.
Inspect the current repository for this task, but do not edit files.

Task:
{task_text}

Return concise findings: relevant files, likely change areas, risks, and test hints."""
    _ensure_prompt_within_limit(prompt, _prompt_limit(project_config, "plan_max_chars", 8000), "explore")
    raw_response = _client(project_config).send_message(
        session_id,
        prompt,
        _agent(project_config, "explorer", "explore"),
        timeout=_timeout(project_config, "explore"),
    )
    result = compact_explore_result(raw_response, _prompt_limit(project_config, "section_max_chars", 2500))
    result["prompt_chars"] = len(prompt)
    return result


def plan(
    session_id: str,
    task_text: str | dict[str, Any],
    explore_result: dict[str, Any],
    architect_plan: dict[str, Any],
    project_config: dict[str, Any],
) -> dict[str, Any]:
    repo_summary = repo_fact_summary_from_explore(explore_result, _prompt_limit(project_config, "section_max_chars", 2500))
    task_contract = (
        compact_task_contract(task_text)
        if isinstance(task_text, dict)
        else build_task_contract(str(task_text), project_config, repo_summary, architect_plan=architect_plan)
    )
    payload = {
        "task_contract": task_contract,
        "repo_summary": repo_summary,
        "architect_plan_summary": {
            "summary": (architect_plan or {}).get("summary", ""),
            "execution_plan": (architect_plan or {}).get("execution_plan", []),
            "constraints": (architect_plan or {}).get("constraints", []),
        },
    }
    prompt = f"""You are the OpenCode planning agent for a personal local workflow.
Create an execution plan only. Do not edit files.

{json.dumps(payload, ensure_ascii=False, indent=2)}

Return a concise implementation plan for the build agent."""
    _ensure_prompt_within_limit(prompt, _prompt_limit(project_config, "plan_max_chars", 8000), "opencode_plan")
    raw_response = _client(project_config).send_message(
        session_id,
        prompt,
        _agent(project_config, "planner", "plan"),
        timeout=_timeout(project_config, "plan"),
    )
    result = compact_plan_result(raw_response, _prompt_limit(project_config, "section_max_chars", 2500))
    result["prompt_chars"] = len(prompt)
    return result


def build(session_id: str, prompt: str, project_config: dict[str, Any]) -> dict[str, Any]:
    _ensure_prompt_within_limit(prompt, _prompt_limit(project_config, "build_max_chars", 12000), "build")
    raw_response = _client(project_config).send_message(
        session_id,
        prompt,
        _agent(project_config, "coder", "build"),
        timeout=_timeout(project_config, "build"),
    )
    result = compact_build_result(raw_response)
    result["prompt_chars"] = len(prompt)
    return result


def repair(session_id: str, retry_prompt: str, project_config: dict[str, Any]) -> dict[str, Any]:
    _ensure_prompt_within_limit(retry_prompt, _prompt_limit(project_config, "retry_max_chars", 8000), "repair")
    raw_response = _client(project_config).send_message(
        session_id,
        retry_prompt,
        _agent(project_config, "repairer", "build"),
        timeout=_timeout(project_config, "repair"),
    )
    result = compact_build_result(raw_response)
    result["prompt_chars"] = len(retry_prompt)
    return result


def validate(
    session_id: str,
    task_text: str | dict[str, Any],
    quality_result: dict[str, Any],
    project_config: dict[str, Any],
    repo_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    task_contract = (
        compact_task_contract(task_text)
        if isinstance(task_text, dict)
        else build_task_contract(str(task_text), project_config, repo_summary or {})
    )
    test = quality_result.get("test", {}) or {}
    lint = quality_result.get("lint", {}) or {}
    payload = {
        "task_contract": task_contract,
        "repo_summary": sanitize_stage_payload(repo_summary or {}),
        "changed_files": quality_result.get("changed_files", []),
        "git_diff_stat": quality_result.get("git_diff_stat", ""),
        "diff_excerpt": str(quality_result.get("diff", ""))[-16000:],
        "quality": {
            "passed": quality_result.get("passed"),
            "test": {
                "enabled": test.get("enabled"),
                "passed": test.get("passed"),
                "cmd": test.get("cmd", ""),
                "returncode": test.get("returncode"),
                "stdout_tail": str(test.get("stdout", ""))[-2000:],
                "stderr_tail": str(test.get("stderr", ""))[-2000:],
            },
            "lint": {
                "enabled": lint.get("enabled"),
                "passed": lint.get("passed"),
                "cmd": lint.get("cmd", ""),
                "returncode": lint.get("returncode"),
                "stdout_tail": str(lint.get("stdout", ""))[-1200:],
                "stderr_tail": str(lint.get("stderr", ""))[-1200:],
            },
            "file_policy": quality_result.get("file_policy", {}),
            "bad_patterns": quality_result.get("bad_patterns", {}),
        },
    }
    prompt = f"""You are the validation reviewer in a personal local multi-role programming workflow.
Do not edit files. Judge whether the actual diff fully satisfies the user's original task intent.

Return strict JSON only:
{{
  "passed": true,
  "score": 90,
  "summary": "...",
  "blocking_issues": [],
  "non_blocking_issues": [],
  "retry_instruction": ""
}}

Validation input:
{json.dumps(payload, ensure_ascii=False, indent=2)}
"""
    _ensure_prompt_within_limit(prompt, _prompt_limit(project_config, "plan_max_chars", 8000), "validate")
    raw_response = _client(project_config).send_message(
        session_id,
        prompt,
        _agent(project_config, "validator", "general"),
        timeout=_timeout(project_config, "validate"),
    )
    result = compact_validator_result(raw_response, _prompt_limit(project_config, "section_max_chars", 2500))
    result["passed"] = bool(result.get("passed", False))
    result["score"] = int(result.get("score", 0) or 0)
    result.setdefault("blocking_issues", [])
    result.setdefault("non_blocking_issues", [])
    result.setdefault("retry_instruction", "")
    result["prompt_chars"] = len(prompt)
    return result

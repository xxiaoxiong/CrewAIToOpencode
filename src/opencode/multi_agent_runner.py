from __future__ import annotations

import json
from typing import Any

from src.opencode.client import OpenCodeClient
from src.orchestration.stage_artifacts import (
    compact_text,
    make_build_artifact,
    make_explore_artifact,
    make_plan_artifact,
    make_validation_artifact,
    make_validation_fallback,
    repo_facts_from_artifact,
    sanitize_stage_value,
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
    _ensure_prompt_within_limit(prompt, _prompt_limit(project_config, "plan_max_chars", 5000), "explore")
    response = _client(project_config).send_message(
        session_id,
        prompt,
        _agent(project_config, "explorer", "explore"),
        timeout=_timeout(project_config, "explore"),
    )
    artifact = make_explore_artifact(response, _prompt_limit(project_config, "section_max_chars", 1800))
    artifact["prompt_chars"] = len(prompt)
    return artifact


def plan(
    session_id: str,
    task_text: str | dict[str, Any],
    explore_artifact: dict[str, Any],
    architect_plan: dict[str, Any],
    project_config: dict[str, Any],
) -> dict[str, Any]:
    repo_summary = repo_facts_from_artifact(explore_artifact, _prompt_limit(project_config, "section_max_chars", 1800))
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
    _ensure_prompt_within_limit(prompt, _prompt_limit(project_config, "plan_max_chars", 5000), "opencode_plan")
    response = _client(project_config).send_message(
        session_id,
        prompt,
        _agent(project_config, "planner", "plan"),
        timeout=_timeout(project_config, "plan"),
    )
    artifact = make_plan_artifact(response, _prompt_limit(project_config, "section_max_chars", 1800))
    artifact["prompt_chars"] = len(prompt)
    return artifact


def build(session_id: str, prompt: str, project_config: dict[str, Any]) -> dict[str, Any]:
    _ensure_prompt_within_limit(prompt, _prompt_limit(project_config, "build_max_chars", 6000), "build")
    response = _client(project_config).send_message(
        session_id,
        prompt,
        _agent(project_config, "coder", "build"),
        timeout=_timeout(project_config, "build"),
    )
    artifact = make_build_artifact(response, "build")
    artifact["prompt_chars"] = len(prompt)
    return artifact


def repair(session_id: str, retry_prompt: str, project_config: dict[str, Any]) -> dict[str, Any]:
    _ensure_prompt_within_limit(retry_prompt, _prompt_limit(project_config, "retry_max_chars", 4000), "repair")
    response = _client(project_config).send_message(
        session_id,
        retry_prompt,
        _agent(project_config, "repairer", "build"),
        timeout=_timeout(project_config, "repair"),
    )
    artifact = make_build_artifact(response, "repair")
    artifact["prompt_chars"] = len(retry_prompt)
    return artifact


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
        "repo_summary": sanitize_stage_value(repo_summary or {}),
        "changed_files": quality_result.get("changed_files", []),
        "git_diff_stat": quality_result.get("git_diff_stat", ""),
        "diff_excerpt": compact_text(str(quality_result.get("diff", "")), 1800),
        "quality": {
            "passed": quality_result.get("passed"),
            "test": {
                "enabled": test.get("enabled"),
                "passed": test.get("passed"),
                "cmd": test.get("cmd", ""),
                "returncode": test.get("returncode"),
                "stdout_tail": compact_text(str(test.get("stdout", "")), 800),
                "stderr_tail": compact_text(str(test.get("stderr", "")), 800),
            },
            "lint": {
                "enabled": lint.get("enabled"),
                "passed": lint.get("passed"),
                "cmd": lint.get("cmd", ""),
                "returncode": lint.get("returncode"),
                "stdout_tail": compact_text(str(lint.get("stdout", "")), 600),
                "stderr_tail": compact_text(str(lint.get("stderr", "")), 600),
            },
            "file_policy": quality_result.get("file_policy", {}),
            "bad_patterns": quality_result.get("bad_patterns", {}),
        },
    }
    prompt = f"""You are the validation reviewer in a personal local multi-role programming workflow.
Do not edit files. Judge whether the actual diff fully satisfies the user's original task intent.

Return strict JSON only:
{{
  "stage": "validate",
  "passed": true,
  "score": 90,
  "criteria_results": [{{"criterion": "...", "passed": true, "evidence": "..."}}],
  "missing_files": [],
  "blocking_issues": [],
  "retry_instruction": ""
}}

Validation input:
{json.dumps(payload, ensure_ascii=False, indent=2)}
"""
    _ensure_prompt_within_limit(prompt, _prompt_limit(project_config, "plan_max_chars", 5000), "validate")
    response = _client(project_config).send_message(
        session_id,
        prompt,
        _agent(project_config, "validator", "general"),
        timeout=_timeout(project_config, "validate"),
    )
    changed_files = [str(path) for path in quality_result.get("changed_files", []) or []]
    artifact = make_validation_artifact(
        response,
        task_contract,
        changed_files,
        _prompt_limit(project_config, "section_max_chars", 1800),
    )
    if not artifact.get("raw_text_truncated"):
        artifact = make_validation_fallback(task_contract, changed_files, "Validator returned no text.")
    artifact["prompt_chars"] = len(prompt)
    return artifact

from __future__ import annotations

import json
from typing import Any

from src.agents.json_utils import parse_json_object
from src.opencode.client import OpenCodeClient


def _agent(project_config: dict[str, Any], key: str, fallback: str) -> str:
    return str((project_config.get("opencode_agents", {}) or {}).get(key) or fallback)


def _client(project_config: dict[str, Any]) -> OpenCodeClient:
    return OpenCodeClient.from_project_config(project_config)


def explore(session_id: str, task_text: str, project_config: dict[str, Any]) -> dict[str, Any]:
    prompt = f"""You are the OpenCode explore agent for a personal local workflow.
Inspect the current repository for this task, but do not edit files.

Task:
{task_text}

Return concise findings: relevant files, likely change areas, risks, and test hints."""
    return _client(project_config).send_message(session_id, prompt, _agent(project_config, "explorer", "explore"))


def plan(
    session_id: str,
    task_text: str,
    explore_result: dict[str, Any],
    architect_plan: dict[str, Any],
    project_config: dict[str, Any],
) -> dict[str, Any]:
    payload = {
        "task": task_text,
        "explore_result": explore_result,
        "architect_plan": architect_plan,
    }
    prompt = f"""You are the OpenCode planning agent for a personal local workflow.
Create an execution plan only. Do not edit files.

{json.dumps(payload, ensure_ascii=False, indent=2)}

Return a concise implementation plan for the build agent."""
    return _client(project_config).send_message(session_id, prompt, _agent(project_config, "planner", "plan"))


def build(session_id: str, prompt: str, project_config: dict[str, Any]) -> dict[str, Any]:
    return _client(project_config).send_message(session_id, prompt, _agent(project_config, "coder", "build"))


def repair(session_id: str, retry_prompt: str, project_config: dict[str, Any]) -> dict[str, Any]:
    return _client(project_config).send_message(session_id, retry_prompt, _agent(project_config, "repairer", "build"))


def _response_text(response: dict[str, Any]) -> str:
    texts: list[str] = []
    for part in response.get("parts", []) or []:
        if isinstance(part, dict) and part.get("text"):
            texts.append(str(part["text"]))
    return "\n".join(texts) or json.dumps(response, ensure_ascii=False)


def validate(
    session_id: str,
    task_text: str,
    quality_result: dict[str, Any],
    project_config: dict[str, Any],
) -> dict[str, Any]:
    payload = {
        "task": task_text,
        "changed_files": quality_result.get("changed_files", []),
        "git_diff_stat": quality_result.get("git_diff_stat", ""),
        "diff": str(quality_result.get("diff", ""))[-20000:],
        "quality": {
            "passed": quality_result.get("passed"),
            "test": quality_result.get("test", {}),
            "lint": quality_result.get("lint", {}),
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
    raw_response = _client(project_config).send_message(
        session_id,
        prompt,
        _agent(project_config, "validator", "general"),
    )
    raw_text = _response_text(raw_response)
    result = parse_json_object(
        raw_text,
        {
            "passed": False,
            "score": 0,
            "summary": "Validator did not return valid JSON.",
            "blocking_issues": ["Validator output was not valid JSON."],
            "non_blocking_issues": [],
            "retry_instruction": "Re-check the task against the diff and return strict JSON validation.",
            "raw": raw_text,
        },
    )
    result["passed"] = bool(result.get("passed", False))
    result["score"] = int(result.get("score", 0) or 0)
    result.setdefault("blocking_issues", [])
    result.setdefault("non_blocking_issues", [])
    result.setdefault("retry_instruction", "")
    result["raw_response"] = raw_response
    return result

from __future__ import annotations

import json
from typing import Any

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

from __future__ import annotations

import json
import os
from typing import Any

from src.agents.json_utils import coerce_string_list, parse_json_object
from src.agents.llm_factory import create_llm


def _fallback_plan(task_text: str, project_config: dict[str, Any], reason: str = "") -> dict[str, Any]:
    allowed = coerce_string_list(project_config.get("allowed_write_paths", []))
    denied = coerce_string_list(project_config.get("denied_paths", []))
    constraints = [f"Only modify allowed paths: {', '.join(allowed) or 'none configured'}"]
    if denied:
        constraints.append(f"Do not modify denied paths: {', '.join(denied)}")
    return {
        "passed": True,
        "summary": "Deterministic planning fallback generated without CrewAI.",
        "affected_areas": allowed,
        "execution_plan": [
            "Inspect the files relevant to the task.",
            "Make the smallest change needed to satisfy the task.",
            "Run the configured validation command.",
        ],
        "constraints": constraints,
        "opencode_instruction": (
            f"Complete the task with minimal edits. Task: {task_text}. "
            f"Allowed paths: {', '.join(allowed) or 'none configured'}."
        ),
        "raw": reason or "architect fallback",
    }


def _build_prompt(task_text: str, project_config: dict[str, Any], repo_context: dict[str, Any]) -> str:
    payload = {
        "task": task_text,
        "project": {
            "id": project_config.get("id"),
            "repo_path": project_config.get("repo_path"),
            "allowed_write_paths": project_config.get("allowed_write_paths", []),
            "denied_paths": project_config.get("denied_paths", []),
            "test_command": project_config.get("test_command", ""),
        },
        "repo_context": repo_context,
    }
    return (
        "You are an Architect Agent. Produce strict JSON only with keys: "
        "passed, summary, affected_areas, execution_plan, constraints, opencode_instruction.\n"
        f"Input:\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )


def _run_crewai(prompt: str, project_config: dict[str, Any]) -> str:
    from crewai import Agent, Crew, Task

    llm = create_llm(project_config)
    agent = Agent(
        role="Software architect",
        goal="Plan a minimal, safe code change for OpenCode to execute.",
        backstory="You produce concise implementation plans and strict JSON.",
        verbose=False,
        llm=llm,
    )
    task = Task(description=prompt, expected_output="Strict JSON planning result.", agent=agent)
    crew = Crew(agents=[agent], tasks=[task], verbose=False)
    return str(crew.kickoff())


def build_architect_plan(
    task_text: str,
    project_config: dict[str, Any],
    repo_context: dict[str, Any],
) -> dict[str, Any]:
    if os.getenv("CREWAI_DISABLE_LLM", "").lower() in {"1", "true", "yes"}:
        return _fallback_plan(task_text, project_config, "CREWAI_DISABLE_LLM is set")

    try:
        raw = _run_crewai(_build_prompt(task_text, project_config, repo_context), project_config)
    except Exception as exc:
        return _fallback_plan(task_text, project_config, f"Architect Agent fallback: {exc}")

    fallback = _fallback_plan(task_text, project_config, "invalid architect JSON")
    result = parse_json_object(raw, fallback)
    result["passed"] = bool(result.get("passed", False))
    result["affected_areas"] = coerce_string_list(result.get("affected_areas", []))
    result["execution_plan"] = coerce_string_list(result.get("execution_plan", []))
    result["constraints"] = coerce_string_list(result.get("constraints", []))
    result["opencode_instruction"] = str(result.get("opencode_instruction", "") or fallback["opencode_instruction"])
    return result

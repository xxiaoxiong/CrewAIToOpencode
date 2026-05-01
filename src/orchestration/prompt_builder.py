from __future__ import annotations

import json
from typing import Any

from src.orchestration.stage_artifacts import compact_text, repo_facts_from_artifact, sanitize_stage_value
from src.orchestration.task_contract import build_task_contract, compact_task_contract


def _list_lines(values: list[str] | None) -> str:
    if not values:
        return "- none configured"
    return "\n".join(f"- {value}" for value in values)


def _real_project_requirement() -> str:
    return """
[Real Project File Requirement]
Create actual runnable project files when the task asks for an application, frontend, website, or project from scratch; do not satisfy it by only writing README text.
For JavaScript frontend projects, include the files that fit the requested stack, such as:
- package.json
- index.html
- src/main.jsx or src/main.tsx
- src/App.jsx or src/App.tsx
- a CSS/style file
- README.md
Use additional folders such as src/, public/, docs/, or data files when they are useful for the task.
"""


def _json_block(payload: dict[str, Any], max_chars: int) -> str:
    body = json.dumps(sanitize_stage_value(payload), ensure_ascii=False, indent=2)
    if len(body) > max_chars:
        return compact_text(body, max_chars=max_chars)
    return body


def _plan_lines(architect_plan: dict[str, Any] | None, plan_artifact: dict[str, Any] | None, max_chars: int) -> str:
    items: list[str] = []
    if architect_plan:
        if architect_plan.get("summary"):
            items.append(f"Architect summary: {architect_plan.get('summary')}")
        items.extend(str(item) for item in architect_plan.get("execution_plan", []) or [])
        if architect_plan.get("opencode_instruction"):
            items.append(str(architect_plan["opencode_instruction"]))
    if plan_artifact:
        if plan_artifact.get("summary"):
            items.append(f"Plan summary: {plan_artifact.get('summary')}")
        items.extend(str(item) for item in plan_artifact.get("implementation_steps", []) or [])
    return compact_text(_list_lines(items) if items else "- Follow the Task Contract.", max_chars=max_chars)


def _limit_prompt(prompt: str, max_chars: int) -> str:
    if len(prompt) <= max_chars:
        return prompt
    return compact_text(prompt, max_chars=max_chars)


def build_initial_prompt(
    task_text: str,
    project_config: dict,
    plan_result: dict[str, Any] | None = None,
    explore_result: dict[str, Any] | None = None,
    opencode_plan: dict[str, Any] | None = None,
    task_contract: dict[str, Any] | None = None,
    repo_summary: dict[str, Any] | None = None,
) -> str:
    limits = project_config.get("prompt_limits", {}) or {}
    section_max_chars = int(limits.get("section_max_chars", 1800))
    build_max_chars = int(limits.get("build_max_chars", 6000))
    repo_facts = repo_facts_from_artifact(repo_summary or explore_result or {}, max_chars=section_max_chars)
    contract = compact_task_contract(
        task_contract
        or build_task_contract(
            task_text,
            project_config,
            repo_facts,
            architect_plan=plan_result,
            opencode_plan=opencode_plan,
        )
    )
    denied_paths = _list_lines(contract.get("denied_paths") or project_config.get("denied_paths", []))
    validation_commands = contract.get("validation_commands", [])
    validation_lines = _list_lines(validation_commands) if validation_commands else project_config.get("test_command", "")
    implementation_plan = _plan_lines(plan_result, opencode_plan, section_max_chars)

    prompt = f"""You are the OpenCode build execution agent. Complete the task in the current repository.

[Task Goal]
{compact_text(task_text, 1000)}

[Task Contract]
{_json_block(contract, min(max(section_max_chars, 1200), 2200))}

[Repository Facts]
{_json_block(repo_facts, section_max_chars)}

[Implementation Plan]
{implementation_plan}

{_real_project_requirement()}

[Execution Rules]
- Read the relevant code before editing.
- Create or modify the files needed inside the current repository to fully complete the task.
- Do not modify denied paths:
{denied_paths}
- Do not only write README to satisfy a real project creation task.
- Do not delete, skip, weaken, or bypass tests.
- Do not introduce TODO, FIXME, HACK, debugger, console.log, secrets, or hardcoded credentials.
- Run the configured validation command:
{validation_lines or "no test command configured"}
- If validation fails, use the logs to fix the root cause.
- At the end, briefly report changed files and validation result.

Start now."""
    return _limit_prompt(prompt, build_max_chars)


def build_retry_prompt(
    task_text: str,
    quality_result: dict,
    review_result: dict,
    iteration: int,
    tester_analysis: dict[str, Any] | None = None,
    validator_result: dict[str, Any] | None = None,
    task_contract: dict[str, Any] | None = None,
) -> str:
    limits = {"retry_max_chars": 4000, "section_max_chars": 1800}
    test = quality_result.get("test", {}) or {}
    lint = quality_result.get("lint", {}) or {}
    blocking = review_result.get("blocking_issues", []) or []
    validator_blocking = (validator_result or {}).get("blocking_issues", []) or []
    retry_instruction = (
        review_result.get("retry_instruction")
        or (validator_result or {}).get("retry_instruction")
        or (tester_analysis or {}).get("retry_instruction")
        or "Fix the listed blocking issues and rerun validation."
    )
    contract = compact_task_contract(
        task_contract
        or build_task_contract(task_text, {"denied_paths": []}, repo_summary={}, architect_plan=None, opencode_plan=None)
    )

    failed_acceptance_items: list[str] = []
    for item in (validator_result or {}).get("criteria_results", []) or []:
        if isinstance(item, dict) and item.get("passed") is False:
            failed_acceptance_items.append(str(item.get("criterion", "")))
    failed_acceptance_items.extend(str(item) for item in (validator_result or {}).get("missing_files", []) or [])
    if test.get("passed") is False:
        failed_acceptance_items.append("Configured test command did not pass.")
    if lint.get("passed") is False:
        failed_acceptance_items.append("Configured lint command did not pass.")
    failed_acceptance_items.extend(str(item) for item in validator_blocking)
    failed_acceptance_items.extend(str(item) for item in blocking)

    quality_summary = {
        "changed_files": quality_result.get("changed_files", []),
        "quality_passed": quality_result.get("passed"),
        "test": {
            "cmd": test.get("cmd", ""),
            "passed": test.get("passed"),
            "stdout_tail": compact_text(str(test.get("stdout", "")), 700),
            "stderr_tail": compact_text(str(test.get("stderr", "")), 700),
        },
        "lint": {
            "cmd": lint.get("cmd", ""),
            "passed": lint.get("passed"),
            "stdout_tail": compact_text(str(lint.get("stdout", "")), 500),
            "stderr_tail": compact_text(str(lint.get("stderr", "")), 500),
        },
    }

    prompt = f"""You are the OpenCode build execution agent. The previous attempt did not pass validation.

[Original Task]
{compact_text(task_text, 900)}

[Task Contract]
{_json_block(contract, 1500)}

[Failed Acceptance Items]
{_json_block({"items": failed_acceptance_items}, 900)}

[Quality Gate Summary]
{_json_block(quality_summary, 1200)}

[Validator / Reviewer Blocking Issues]
{_json_block({
    "validator_blocking_issues": validator_blocking,
    "reviewer_blocking_issues": blocking,
    "tester_root_cause": (tester_analysis or {}).get("root_cause_summary", ""),
}, 1000)}

[Retry Instruction]
{compact_text(retry_instruction, 500)}

[Retry Requirements]
- Fix only the listed blocking issues.
- Do not expand scope or introduce unrelated changes.
- Do not touch denied paths.
- Do not skip, delete, or weaken tests.
- Rerun validation and report the result.
Continue in the same session."""
    return _limit_prompt(prompt, limits["retry_max_chars"])

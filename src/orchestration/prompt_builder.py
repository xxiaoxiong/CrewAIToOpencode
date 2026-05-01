from __future__ import annotations

import json
from typing import Any

from src.orchestration.context_compactor import compact_text, repo_fact_summary_from_explore, sanitize_stage_payload
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
    body = json.dumps(sanitize_stage_payload(payload), ensure_ascii=False, indent=2)
    if len(body) > max_chars:
        return compact_text(body, max_chars=max_chars)
    return body


def build_initial_prompt(
    task_text: str,
    project_config: dict,
    plan_result: dict[str, Any] | None = None,
    explore_result: dict[str, Any] | None = None,
    opencode_plan: dict[str, Any] | None = None,
    task_contract: dict[str, Any] | None = None,
    repo_summary: dict[str, Any] | None = None,
) -> str:
    section_max_chars = int((project_config.get("prompt_limits", {}) or {}).get("section_max_chars", 2500))
    repo_facts = repo_fact_summary_from_explore(repo_summary or explore_result or {}, max_chars=section_max_chars)
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

    legacy_plan_note = ""
    if plan_result:
        legacy_plan_note += "\n[Architect Plan]\nIncluded in the Task Contract acceptance criteria.\n"
    if opencode_plan:
        legacy_plan_note += "\n[OpenCode Plan Summary]\nIncluded in the Task Contract acceptance criteria.\n"

    return f"""You are the OpenCode build execution agent. Complete the task in the current repository.

[Task Goal]
{task_text}

[Task Contract]
{_json_block(contract, max(section_max_chars, 1200))}

[Repository Fact Summary]
{_json_block(repo_facts, section_max_chars)}

[OpenCode Explore Summary]
This section is intentionally limited to the repository fact summary above.
{legacy_plan_note}
{_real_project_requirement()}
[Execution Constraints]
1. Read the relevant code before editing.
2. Create or modify any project files needed inside the current repository/work directory to fully complete the task.
3. Avoid broad unrelated refactors.
4. Never modify these denied paths:
{denied_paths}
5. Do not delete, skip, weaken, or bypass tests to make validation pass.
6. Do not introduce TODO, FIXME, HACK, debugger, console.log, secrets, or hardcoded credentials.
7. After editing, run the configured validation command:
{validation_lines or "no test command configured"}
8. If validation fails, use the logs to fix the root cause.
9. At the end, briefly report changed files, rationale, and validation result.

[Output Requirement]
Keep the final response concise and factual.
Start now."""


def build_retry_prompt(
    task_text: str,
    quality_result: dict,
    review_result: dict,
    iteration: int,
    tester_analysis: dict[str, Any] | None = None,
    validator_result: dict[str, Any] | None = None,
    task_contract: dict[str, Any] | None = None,
) -> str:
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
    if not quality_result.get("changed_files"):
        failed_acceptance_items.append("No changed files were detected.")
    if test.get("passed") is False:
        failed_acceptance_items.append("Configured test command did not pass.")
    if lint.get("passed") is False:
        failed_acceptance_items.append("Configured lint command did not pass.")
    failed_acceptance_items.extend(str(item) for item in validator_blocking)
    failed_acceptance_items.extend(str(item) for item in blocking)

    test_failure_summary = {
        "test_command": test.get("cmd", ""),
        "test_passed": test.get("passed"),
        "test_stdout_tail": str(test.get("stdout", ""))[-2000:],
        "test_stderr_tail": str(test.get("stderr", ""))[-2000:],
        "lint_command": lint.get("cmd", ""),
        "lint_passed": lint.get("passed"),
        "lint_stdout_tail": str(lint.get("stdout", ""))[-1200:],
        "lint_stderr_tail": str(lint.get("stderr", ""))[-1200:],
        "tester_failure_type": (tester_analysis or {}).get("failure_type", ""),
        "tester_root_cause": (tester_analysis or {}).get("root_cause_summary", ""),
    }

    return f"""You are the OpenCode build execution agent. The previous attempt did not pass validation.

[Original Task]
{task_text}

[Task Contract]
{json.dumps(contract, ensure_ascii=False, indent=2)}

[Retry Iteration]
{iteration}

[Failed Acceptance Items]
{json.dumps(failed_acceptance_items, ensure_ascii=False, indent=2)}

[Test Failure Summary]
{json.dumps(test_failure_summary, ensure_ascii=False, indent=2)}

[Tester Analyst]
{json.dumps({
    "failure_type": (tester_analysis or {}).get("failure_type", ""),
    "root_cause_summary": (tester_analysis or {}).get("root_cause_summary", ""),
    "retry_instruction": (tester_analysis or {}).get("retry_instruction", ""),
}, ensure_ascii=False, indent=2)}

[Validation Reviewer]
{json.dumps({
    "blocking_issues": validator_blocking,
    "retry_instruction": (validator_result or {}).get("retry_instruction", ""),
}, ensure_ascii=False, indent=2)}

[Reviewer Blocking Issues]
{json.dumps(blocking, ensure_ascii=False, indent=2)}

[Retry Instruction]
{retry_instruction}

[Retry Requirements]
1. Fix only the listed failure causes.
2. Do not expand scope or introduce unrelated changes.
3. You may create or modify needed project files in the current repository, but do not touch denied paths.
4. Do not skip, delete, or weaken tests.
5. Rerun validation and report the result.
Continue in the same session."""

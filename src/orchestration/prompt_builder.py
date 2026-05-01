from __future__ import annotations

import json
from typing import Any

from src.orchestration.context_compactor import compact_text, extract_opencode_text


def _list_lines(values: list[str] | None) -> str:
    if not values:
        return "- none configured"
    return "\n".join(f"- {value}" for value in values)


def _real_project_requirement() -> str:
    return """
[Real Project File Requirement]
If the task asks you to create an application, frontend, website, or project from scratch, create actual runnable project files; do not satisfy it by only writing README text.
For JavaScript frontend projects, include the files that fit the requested stack, such as:
- package.json
- index.html
- src/main.jsx or src/main.tsx
- src/App.jsx or src/App.tsx
- a CSS/style file
- README.md
Use additional folders such as src/, public/, docs/, or data files when they are useful for the task.
"""


def _plan_section(plan_result: dict[str, Any] | None) -> str:
    if not plan_result:
        return ""
    payload = {
        "summary": plan_result.get("summary", ""),
        "affected_areas": plan_result.get("affected_areas", []),
        "execution_plan": plan_result.get("execution_plan", []),
        "constraints": plan_result.get("constraints", []),
        "opencode_instruction": plan_result.get("opencode_instruction", ""),
    }
    return (
        "\n[Architect Plan]\n"
        "Use this planning context as guidance. OpenCode build remains the only agent allowed to edit files.\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}\n"
    )


def _compact_stage_section(title: str, payload: dict[str, Any] | None, max_chars: int = 2500) -> str:
    if not payload:
        return ""
    allowed_keys = [
        "summary",
        "relevant_files",
        "risks",
        "test_hints",
        "execution_plan",
        "blocking_issues",
        "retry_instruction",
        "raw_text_truncated",
    ]
    compact_payload = {key: payload.get(key) for key in allowed_keys if key in payload}
    if not compact_payload:
        text = extract_opencode_text(payload)
        if text:
            compact_payload = {
                "summary": compact_text(text, max_chars=600),
                "raw_text_truncated": compact_text(text, max_chars=max_chars),
            }
    if not compact_payload:
        return ""
    body = json.dumps(compact_payload, ensure_ascii=False, indent=2)
    if len(body) > max_chars:
        body = compact_text(body, max_chars=max_chars)
    return f"\n[{title}]\n{body}\n"


def build_initial_prompt(
    task_text: str,
    project_config: dict,
    plan_result: dict[str, Any] | None = None,
    explore_result: dict[str, Any] | None = None,
    opencode_plan: dict[str, Any] | None = None,
) -> str:
    denied_paths = _list_lines(project_config.get("denied_paths", []))
    test_command = project_config.get("test_command", "")
    section_max_chars = int((project_config.get("prompt_limits", {}) or {}).get("section_max_chars", 2500))

    return f"""You are the OpenCode build execution agent. Complete the task in the current repository.

[Task Goal]
{task_text}
{_compact_stage_section("OpenCode Explore Summary", explore_result, section_max_chars)}
{_plan_section(plan_result)}
{_compact_stage_section("OpenCode Plan Summary", opencode_plan, section_max_chars)}
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
{test_command or "no test command configured"}
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
) -> str:
    test = quality_result.get("test", {})
    lint = quality_result.get("lint", {})
    blocking = review_result.get("blocking_issues", [])
    validator_blocking = (validator_result or {}).get("blocking_issues", [])
    retry_instruction = (
        review_result.get("retry_instruction")
        or (validator_result or {}).get("retry_instruction")
        or (tester_analysis or {}).get("retry_instruction")
        or ""
    )

    failure_summary = {
        "quality_passed": quality_result.get("passed"),
        "changed_files": quality_result.get("changed_files", []),
        "test_passed": test.get("passed"),
        "lint_passed": lint.get("passed"),
        "tester_failure_type": (tester_analysis or {}).get("failure_type", ""),
        "tester_root_cause": (tester_analysis or {}).get("root_cause_summary", ""),
        "validator_blocking_issues": validator_blocking,
        "reviewer_blocking_issues": blocking,
        "retry_instruction": retry_instruction,
    }

    return f"""You are the OpenCode build execution agent. The previous attempt did not pass validation.

[Original Task]
{task_text}

[Retry Iteration]
{iteration}

[Failure Summary]
{json.dumps(failure_summary, ensure_ascii=False, indent=2)}

[Test Logs]
Command: {test.get("cmd", "")}
stdout:
{test.get("stdout", "")[-2000:]}
stderr:
{test.get("stderr", "")[-2000:]}

[Lint Logs]
Command: {lint.get("cmd", "")}
stdout:
{lint.get("stdout", "")[-2000:]}
stderr:
{lint.get("stderr", "")[-2000:]}

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

[Retry Requirements]
1. Fix only the listed failure causes.
2. Do not expand scope or introduce unrelated changes.
3. You may create or modify needed project files in the current repository, but do not touch denied paths.
4. Do not skip, delete, or weaken tests.
5. Rerun validation and report the result.
Continue in the same session."""

from __future__ import annotations

import json
from typing import Any


def _list_lines(values: list[str] | None) -> str:
    if not values:
        return "- unrestricted"
    return "\n".join(f"- {value}" for value in values)


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


def _stage_section(title: str, payload: dict[str, Any] | None) -> str:
    if not payload:
        return ""
    return f"\n[{title}]\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n"


def build_initial_prompt(
    task_text: str,
    project_config: dict,
    plan_result: dict[str, Any] | None = None,
    explore_result: dict[str, Any] | None = None,
    opencode_plan: dict[str, Any] | None = None,
) -> str:
    allowed_write_paths = _list_lines(project_config.get("allowed_write_paths", []))
    denied_paths = _list_lines(project_config.get("denied_paths", []))
    test_command = project_config.get("test_command", "")

    return f"""You are the OpenCode build execution agent. Complete the task in the current repository.

[Task Goal]
{task_text}
{_stage_section("OpenCode Explore Result", explore_result)}
{_plan_section(plan_result)}
{_stage_section("OpenCode Plan Result", opencode_plan)}
[Execution Constraints]
1. Read the relevant code before editing.
2. Make the smallest necessary change and avoid broad refactors.
3. Only modify these allowed paths:
{allowed_write_paths}
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
    file_policy = quality_result.get("file_policy", {})
    bad_patterns = quality_result.get("bad_patterns", {})
    blocking = review_result.get("blocking_issues", [])

    failure_summary = {
        "quality_passed": quality_result.get("passed"),
        "changed_files": quality_result.get("changed_files", []),
        "test_passed": test.get("passed"),
        "lint_passed": lint.get("passed"),
        "file_policy": file_policy,
        "bad_patterns": bad_patterns,
        "tester_analysis": tester_analysis or {},
        "validator_result": validator_result or {},
        "review_passed": review_result.get("passed"),
        "review_blocking_issues": blocking,
        "review_retry_instruction": review_result.get("retry_instruction", ""),
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
{test.get("stdout", "")[-4000:]}
stderr:
{test.get("stderr", "")[-4000:]}

[Lint Logs]
Command: {lint.get("cmd", "")}
stdout:
{lint.get("stdout", "")[-4000:]}
stderr:
{lint.get("stderr", "")[-4000:]}

[Tester Analyst]
{json.dumps(tester_analysis or {}, ensure_ascii=False, indent=2)}

[Validation Reviewer]
{json.dumps(validator_result or {}, ensure_ascii=False, indent=2)}

[Reviewer Blocking Issues]
{json.dumps(blocking, ensure_ascii=False, indent=2)}

[Retry Requirements]
1. Fix only the listed failure causes.
2. Do not expand scope or introduce unrelated changes.
3. Do not modify files outside the allowed paths.
4. Do not skip, delete, or weaken tests.
5. Rerun validation and report the result.
Continue in the same session."""

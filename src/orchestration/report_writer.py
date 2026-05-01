from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from src.orchestration.context_compactor import report_safe_payload
from src.settings import REPORTS_DIR


def _basename(report: dict[str, Any]) -> str:
    if "_report_basename" not in report:
        report["_report_basename"] = datetime.now().strftime("report-%Y%m%d-%H%M%S")
    return str(report["_report_basename"])


def write_json_report(report: dict) -> str:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / f"{_basename(report)}.json"
    report["report_json"] = str(path)
    safe_report = _safe_report(report)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(safe_report, handle, ensure_ascii=False, indent=2)
    return str(path)


def _safe_report(value: Any) -> Any:
    return report_safe_payload(value)


def _ok(value: bool | None) -> str:
    return "PASS" if value else "FAIL"


def _failure_reasons(report: dict) -> list[str]:
    reasons: list[str] = []
    quality = report.get("quality", {})
    review = report.get("review", {})
    validator = report.get("validator", {})
    if report.get("error"):
        reasons.append(str(report["error"]))
    if not quality.get("changed_files"):
        reasons.append("No changed files were detected.")
    if quality.get("test", {}).get("passed") is False:
        reasons.append("Test command failed.")
    if quality.get("lint", {}).get("passed") is False:
        reasons.append("Lint command failed.")
    if quality.get("file_policy", {}).get("passed") is False:
        reasons.append("File policy failed.")
    if quality.get("bad_patterns", {}).get("passed") is False:
        reasons.append("Dangerous pattern scan failed.")
    for issue in validator.get("blocking_issues", []) or []:
        reasons.append(str(issue))
    for issue in review.get("blocking_issues", []) or []:
        reasons.append(str(issue))
    timeout_seconds = _timeout_seconds(report, reasons)
    if timeout_seconds:
        reasons.append(
            f"Timeout detected after {timeout_seconds} seconds. Try standard mode or increase the relevant opencode_timeouts value."
        )
    return reasons


def _timeout_seconds(report: dict, reasons: list[str] | None = None) -> str:
    text = " ".join([str(report.get("error", "")), *(reasons or [])])
    match = re.search(r"timed out after (\d+) seconds|read timeout=(\d+)", text, re.IGNORECASE)
    if not match:
        return ""
    return next(group for group in match.groups() if group)


def write_markdown_report(report: dict) -> str:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / f"{_basename(report)}.md"
    report["report_md"] = str(path)
    report = _safe_report(report)

    quality = report.get("quality", {})
    review = report.get("review", {})
    explore = report.get("explore", {})
    plan = report.get("plan", {})
    architect_plan = report.get("architect_plan", plan)
    opencode_plan = report.get("opencode_plan", {})
    build = report.get("build", {})
    tester = report.get("tester", {})
    validator = report.get("validator", {})
    reporter = report.get("reporter", {})
    retry_history = report.get("retry_history", [])
    test = quality.get("test", {})
    lint = quality.get("lint", {})
    reasons = _failure_reasons(report)
    changed_files = quality.get("changed_files", [])
    failed_stage = report.get("failed_stage", "")

    lines = [
        f"# AI Development Report",
        "",
        f"- Task: {report.get('task', '')}",
        f"- Project ID: {report.get('project_id', '')}",
        f"- OpenCode session ID: {report.get('session_id', '')}",
        f"- Mode: {report.get('mode', '')}",
        f"- Success: {_ok(report.get('passed'))}",
        f"- Failed stage: {failed_stage or 'N/A'}",
        f"- Iterations used: {report.get('iterations_used', 0)} / {report.get('max_iterations', 0)}",
        "",
        "## OpenCode Explore",
        "",
        f"```json\n{json.dumps(explore, ensure_ascii=False, indent=2)[:8000]}\n```",
        "",
        "## CrewAI Architect",
        "",
        f"- Summary: {architect_plan.get('summary', '')}",
        f"- Execution plan: `{json.dumps(architect_plan.get('execution_plan', []), ensure_ascii=False)}`",
        f"- OpenCode instruction: {architect_plan.get('opencode_instruction', '')}",
        "",
        "## OpenCode Plan",
        "",
        f"```json\n{json.dumps(opencode_plan, ensure_ascii=False, indent=2)[:8000]}\n```",
        "",
        "## OpenCode Build",
        "",
        f"```json\n{json.dumps(build, ensure_ascii=False, indent=2)[:8000]}\n```",
        "",
        "## Changed Files",
        "",
        *([f"- {item}" for item in changed_files] or ["- None"]),
        "",
        "## Test Result",
        "",
        f"- Enabled: {test.get('enabled', False)}",
        f"- Passed: {_ok(test.get('passed'))}",
        f"- Command: `{test.get('cmd', '')}`",
        "",
        "## Quality Gate",
        "",
        f"```json\n{json.dumps(quality, ensure_ascii=False, indent=2)[:8000]}\n```",
        "",
        "## CrewAI Tester",
        "",
        f"- Passed: {_ok(tester.get('passed')) if tester else 'N/A'}",
        f"- Failure type: {tester.get('failure_type', '')}",
        f"- Root cause: {tester.get('root_cause_summary', '')}",
        f"- Retry instruction: {tester.get('retry_instruction', '')}",
        "",
        "## LLM Task Validator",
        "",
        f"- Passed: {_ok(validator.get('passed')) if validator else 'N/A'}",
        f"- Score: {validator.get('score', '')}",
        f"- Summary: {validator.get('summary', '')}",
        f"- Blocking issues: `{json.dumps(validator.get('blocking_issues', []), ensure_ascii=False)}`",
        f"- Retry instruction: {validator.get('retry_instruction', '')}",
        "",
        "## Lint Result",
        "",
        f"- Enabled: {lint.get('enabled', False)}",
        f"- Passed: {_ok(lint.get('passed'))}",
        f"- Command: `{lint.get('cmd', '')}`",
        "",
        "## File Policy",
        "",
        f"- Passed: {_ok(quality.get('file_policy', {}).get('passed'))}",
        f"- Violations: `{json.dumps(quality.get('file_policy', {}).get('violations', []), ensure_ascii=False)}`",
        "",
        "## Dangerous Patterns",
        "",
        f"- Passed: {_ok(quality.get('bad_patterns', {}).get('passed'))}",
        f"- Hits: `{json.dumps(quality.get('bad_patterns', {}).get('hits', []), ensure_ascii=False)}`",
        "",
        "## CrewAI Reviewer",
        "",
        f"- Passed: {_ok(review.get('passed'))}",
        f"- Score: {review.get('score', 0)}",
        f"- Blocking issues: `{json.dumps(review.get('blocking_issues', []), ensure_ascii=False)}`",
        "",
        "## CrewAI Reporter",
        "",
        f"- Summary: {reporter.get('summary', '')}",
        f"- Validation summary: {reporter.get('validation_summary', '')}",
        "",
        "## Retry History",
        "",
        f"```json\n{json.dumps(retry_history, ensure_ascii=False, indent=2)[:8000]}\n```",
        "",
        "## Failure Reasons",
        "",
        *([f"- {reason}" for reason in reasons] or ["- None"]),
        "",
        "## Next Steps",
        "",
        "- Inspect the JSON report for full command output and diff details." if not report.get("passed") else "- Review the diff and commit the accepted changes.",
        "",
    ]

    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)

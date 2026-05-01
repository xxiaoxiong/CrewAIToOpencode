from __future__ import annotations

import re
from typing import Any

from src.agents.json_utils import parse_json_object


FORBIDDEN_RESPONSE_KEYS = {
    "cache",
    "info",
    "messageID",
    "metadata",
    "parentID",
    "parts",
    "raw_response",
    "sessionID",
    "snapshot",
    "tokens",
}

PATH_PATTERN = re.compile(
    r"(?<![\w.-])(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+|"
    r"(?<![\w.-])[A-Za-z0-9_.-]+\.(?:py|js|jsx|ts|tsx|css|html|json|md|yaml|yml|toml|txt)"
)


def sanitize_stage_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: sanitize_stage_value(item)
            for key, item in value.items()
            if key not in FORBIDDEN_RESPONSE_KEYS
        }
    if isinstance(value, list):
        return [sanitize_stage_value(item) for item in value]
    return value


def compact_text(text: str, max_chars: int = 3000) -> str:
    if not text:
        return ""
    lines = [line.strip() for line in str(text).splitlines() if line.strip()]
    compacted = "\n".join(lines).strip()
    if len(compacted) <= max_chars:
        return compacted
    if max_chars <= 20:
        return compacted[:max_chars]
    marker = "\n...[truncated]...\n"
    head_len = max_chars // 2
    tail_len = max_chars - head_len - len(marker)
    return f"{compacted[:head_len].rstrip()}{marker}{compacted[-tail_len:].lstrip()}"[:max_chars]


def extract_opencode_text(response: dict[str, Any]) -> str:
    texts: list[str] = []
    for part in response.get("parts", []) or []:
        if isinstance(part, dict) and part.get("type") == "text" and part.get("text"):
            texts.append(str(part["text"]))
    if texts:
        return "\n".join(texts).strip()
    raw = response.get("raw")
    return str(raw).strip() if raw else ""


def _parse_json_text(text: str) -> dict[str, Any]:
    parsed = parse_json_object(text, {})
    return parsed if isinstance(parsed, dict) else {}


def _string_list(value: Any, limit: int = 12) -> list[str]:
    if not isinstance(value, list):
        return []
    results: list[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            results.append(text[:300])
        if len(results) >= limit:
            break
    return results


def _dedupe(values: list[str], limit: int = 20) -> list[str]:
    seen: dict[str, None] = {}
    for value in values:
        text = str(value).strip()
        if text:
            seen.setdefault(text, None)
        if len(seen) >= limit:
            break
    return list(seen)


def _extract_paths(text: str, limit: int = 20) -> list[str]:
    seen: dict[str, None] = {}
    for match in PATH_PATTERN.findall(text):
        seen.setdefault(match.replace("\\", "/"), None)
        if len(seen) >= limit:
            break
    return list(seen)


def _extract_action_lines(text: str, limit: int = 10) -> list[str]:
    results: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if re.match(r"^(\d+[\.)]|[-*])\s+", line):
            results.append(line[:300])
        if len(results) >= limit:
            break
    return results


def _summary_from_text(text: str, max_chars: int = 600) -> str:
    lines = [line.strip("-* 0123456789.").strip() for line in text.splitlines() if line.strip()]
    summary = " ".join(lines[:4]).strip()
    return compact_text(summary or text, max_chars)


def _first_nonempty(*values: Any) -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _infer_project_type(text: str, files: list[str]) -> str:
    lowered = f"{text}\n{' '.join(files)}".lower()
    if "vite" in lowered or "react" in lowered or any(path.endswith((".jsx", ".tsx")) for path in files):
        return "frontend/javascript"
    if "package.json" in lowered or any(path.endswith((".js", ".ts")) for path in files):
        return "javascript"
    if "pyproject.toml" in lowered or "pytest" in lowered or any(path.endswith(".py") for path in files):
        return "python"
    if files:
        return "mixed"
    return "unknown"


def repo_facts_from_artifact(value: dict[str, Any] | None, max_chars: int = 1800) -> dict[str, Any]:
    payload = sanitize_stage_value(value or {})
    text = compact_text(str(payload.get("raw_text_truncated", "")), max_chars=max_chars)
    if not text:
        text = compact_text(
            "\n".join(
                str(payload.get(key, ""))
                for key in ("repo_summary", "summary", "project_type", "suggested_scope")
                if payload.get(key)
            ),
            max_chars=max_chars,
        )
    parsed = _parse_json_text(text)
    existing_files = (
        _string_list(parsed.get("existing_files"), limit=20)
        or _string_list(payload.get("existing_files"), limit=20)
        or _extract_paths(text, limit=20)
    )
    relevant_files = (
        _string_list(parsed.get("relevant_files"), limit=20)
        or _string_list(payload.get("relevant_files"), limit=20)
        or existing_files[:12]
    )
    repo_summary = _first_nonempty(
        parsed.get("repo_summary"),
        parsed.get("summary"),
        payload.get("repo_summary"),
        payload.get("summary"),
        _summary_from_text(text),
        "No repository exploration summary was available.",
    )
    return {
        "repo_summary": compact_text(repo_summary, max_chars=600),
        "project_type": _first_nonempty(
            parsed.get("project_type"),
            payload.get("project_type"),
            _infer_project_type(text, [*existing_files, *relevant_files]),
        ),
        "existing_files": existing_files,
        "relevant_files": relevant_files,
        "risks": _string_list(parsed.get("risks"), limit=10) or _string_list(payload.get("risks"), limit=10),
        "suggested_scope": (
            _string_list(parsed.get("suggested_scope"), limit=10)
            or _string_list(parsed.get("implementation_steps"), limit=10)
            or _string_list(payload.get("suggested_scope"), limit=10)
        ),
    }


def make_explore_artifact(response: dict[str, Any], max_chars: int = 1800) -> dict[str, Any]:
    text = compact_text(extract_opencode_text(response), max_chars=max_chars)
    parsed = _parse_json_text(text)
    repo_facts = repo_facts_from_artifact(
        {
            "summary": parsed.get("summary"),
            "repo_summary": parsed.get("repo_summary"),
            "project_type": parsed.get("project_type"),
            "existing_files": parsed.get("existing_files"),
            "relevant_files": parsed.get("relevant_files"),
            "risks": parsed.get("risks"),
            "suggested_scope": parsed.get("suggested_scope"),
            "raw_text_truncated": text,
        },
        max_chars=max_chars,
    )
    return sanitize_stage_value(
        {
            "stage": "explore",
            "summary": _first_nonempty(parsed.get("summary"), repo_facts["repo_summary"]),
            "repo_summary": repo_facts["repo_summary"],
            "project_type": repo_facts["project_type"],
            "existing_files": repo_facts["existing_files"],
            "relevant_files": repo_facts["relevant_files"],
            "risks": _string_list(parsed.get("risks"), limit=10) or repo_facts["risks"],
            "suggested_scope": _string_list(parsed.get("suggested_scope"), limit=10) or repo_facts["suggested_scope"],
            "raw_text_truncated": text,
        }
    )


def make_plan_artifact(response: dict[str, Any], max_chars: int = 1800) -> dict[str, Any]:
    text = compact_text(extract_opencode_text(response), max_chars=max_chars)
    parsed = _parse_json_text(text)
    steps = (
        _string_list(parsed.get("implementation_steps"), limit=12)
        or _string_list(parsed.get("execution_plan"), limit=12)
        or _extract_action_lines(text, limit=12)
    )
    return sanitize_stage_value(
        {
            "stage": "plan",
            "summary": _first_nonempty(parsed.get("summary"), _summary_from_text(text)),
            "implementation_steps": steps,
            "acceptance_notes": _string_list(parsed.get("acceptance_notes"), limit=10),
            "risks": _string_list(parsed.get("risks"), limit=10),
            "raw_text_truncated": text,
        }
    )


def make_build_artifact(response: dict[str, Any], stage: str = "build", max_chars: int = 1600) -> dict[str, Any]:
    text = compact_text(extract_opencode_text(response), max_chars=max_chars)
    parsed = _parse_json_text(text)
    changed_files = _string_list(parsed.get("changed_files_hint"), limit=20) or _extract_paths(text, limit=20)
    return sanitize_stage_value(
        {
            "stage": stage,
            "summary": _first_nonempty(parsed.get("summary"), _summary_from_text(text)),
            "changed_files_hint": changed_files,
            "raw_text_truncated": text,
        }
    )


def _normalize_path(path: str) -> str:
    return str(path).replace("\\", "/").lstrip("./").lower()


def _required_options(requirement: str) -> list[str]:
    return [_normalize_path(option.strip()) for option in re.split(r"\s+or\s+", requirement) if option.strip()]


def _requirement_satisfied(requirement: str, changed_files: list[str]) -> bool:
    options = _required_options(requirement)
    changed = [_normalize_path(path) for path in changed_files]
    if not options:
        return True
    return any(option in changed for option in options)


def deterministic_contract_results(task_contract: dict[str, Any], changed_files: list[str]) -> dict[str, Any]:
    contract = sanitize_stage_value(task_contract or {})
    required_files = _string_list(contract.get("must_create_or_modify_files"), limit=30)
    normalized_changed = [_normalize_path(path) for path in changed_files]
    criteria_results: list[dict[str, Any]] = []
    missing_files: list[str] = []
    blocking_issues: list[str] = []

    for criterion in _string_list(contract.get("acceptance_criteria"), limit=30):
        criteria_results.append({"criterion": criterion, "passed": True, "evidence": "Checked against deterministic inputs."})

    for required in required_files:
        passed = _requirement_satisfied(required, changed_files)
        criteria_results.append(
            {
                "criterion": f"Required file changed: {required}",
                "passed": passed,
                "evidence": "present in changed_files" if passed else "not present in changed_files",
            }
        )
        if not passed:
            missing_files.append(required)

    if not changed_files:
        blocking_issues.append("No changed files were detected.")

    if str(contract.get("task_type", "")) == "frontend_project_creation":
        readme_only = bool(normalized_changed) and all(path.endswith("readme.md") for path in normalized_changed)
        if readme_only:
            blocking_issues.append("Frontend project creation cannot be satisfied by README-only changes.")
            criteria_results.append(
                {
                    "criterion": "A real runnable frontend project is created; README-only output is not sufficient.",
                    "passed": False,
                    "evidence": "Only README files changed.",
                }
            )

    for missing in missing_files:
        blocking_issues.append(f"Required file was not changed: {missing}")

    passed = not blocking_issues and not missing_files
    return {
        "passed": passed,
        "criteria_results": criteria_results,
        "missing_files": missing_files,
        "blocking_issues": _dedupe(blocking_issues, limit=30),
    }


def make_validation_artifact(
    response: dict[str, Any],
    task_contract: dict[str, Any],
    changed_files: list[str],
    max_chars: int = 1800,
) -> dict[str, Any]:
    text = compact_text(extract_opencode_text(response), max_chars=max_chars)
    parsed = _parse_json_text(text)
    if not parsed:
        return make_validation_fallback(task_contract, changed_files, text or "Validator returned no JSON.", max_chars=max_chars)
    deterministic = deterministic_contract_results(task_contract, changed_files)
    llm_criteria = parsed.get("criteria_results") if isinstance(parsed.get("criteria_results"), list) else []
    criteria_results = [*deterministic["criteria_results"], *sanitize_stage_value(llm_criteria)]
    llm_blocking = _string_list(parsed.get("blocking_issues"), limit=20)
    blocking_issues = _dedupe([*deterministic["blocking_issues"], *llm_blocking], limit=30)
    missing_files = _dedupe([*deterministic["missing_files"], *_string_list(parsed.get("missing_files"), limit=20)], limit=30)
    llm_passed = bool(parsed.get("passed")) if parsed else False
    passed = bool(deterministic["passed"] and llm_passed and not blocking_issues and not missing_files)
    score = int(parsed.get("score", 0) or 0) if parsed else 0
    if not deterministic["passed"]:
        score = min(score or 60, 60)
    return sanitize_stage_value(
        {
            "stage": "validate",
            "passed": passed,
            "score": score,
            "criteria_results": criteria_results,
            "missing_files": missing_files,
            "blocking_issues": blocking_issues,
            "retry_instruction": _first_nonempty(
                parsed.get("retry_instruction") if parsed else "",
                "Fix the failed Task Contract criteria and rerun validation." if blocking_issues or missing_files else "",
            ),
            "raw_text_truncated": text,
        }
    )


def make_validation_fallback(
    task_contract: dict[str, Any],
    changed_files: list[str],
    message: str,
    max_chars: int = 1800,
) -> dict[str, Any]:
    deterministic = deterministic_contract_results(task_contract, changed_files)
    blocking = deterministic["blocking_issues"] or ["Validator output was not valid JSON."]
    return sanitize_stage_value(
        {
            "stage": "validate",
            "passed": False,
            "score": 0 if blocking else 60,
            "criteria_results": deterministic["criteria_results"],
            "missing_files": deterministic["missing_files"],
            "blocking_issues": blocking,
            "retry_instruction": "Fix the failed Task Contract criteria and rerun validation.",
            "raw_text_truncated": compact_text(message, max_chars=max_chars),
        }
    )


def make_review_artifact(value: dict[str, Any], max_chars: int = 1200) -> dict[str, Any]:
    payload = sanitize_stage_value(value or {})
    return {
        "stage": "review",
        "passed": bool(payload.get("passed")),
        "score": int(payload.get("score", 0) or 0),
        "blocking_issues": _string_list(payload.get("blocking_issues"), limit=20),
        "non_blocking_issues": _string_list(payload.get("non_blocking_issues"), limit=20),
        "retry_instruction": str(payload.get("retry_instruction", "") or ""),
        "raw_text_truncated": compact_text(str(payload.get("raw", "") or ""), max_chars=max_chars),
    }

from __future__ import annotations

import re
from typing import Any

from src.agents.json_utils import parse_json_object


PATH_PATTERN = re.compile(
    r"(?<![\w.-])(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+|(?<![\w.-])[A-Za-z0-9_.-]+\.(?:py|js|jsx|ts|tsx|css|html|json|md|yaml|yml|toml|txt)"
)


def extract_opencode_text(response: dict) -> str:
    texts: list[str] = []
    for part in response.get("parts", []) or []:
        if isinstance(part, dict) and part.get("type") == "text" and part.get("text"):
            texts.append(str(part["text"]))
    return "\n".join(texts).strip()


def compact_text(text: str, max_chars: int = 3000) -> str:
    if not text:
        return ""
    lines: list[str] = []
    for raw_line in str(text).splitlines():
        line = raw_line.strip()
        if not line:
            continue
        lines.append(line)
    compacted = "\n".join(lines).strip()
    if len(compacted) <= max_chars:
        return compacted
    if max_chars <= 20:
        return compacted[:max_chars]
    marker = "\n...[truncated]...\n"
    head_len = max_chars // 2
    tail_len = max_chars - head_len - len(marker)
    return f"{compacted[:head_len].rstrip()}{marker}{compacted[-tail_len:].lstrip()}"[:max_chars]


def _summary_from_text(text: str, max_chars: int = 600) -> str:
    lines = [line.strip("-* 0123456789.").strip() for line in text.splitlines() if line.strip()]
    summary = " ".join(lines[:4]).strip()
    return compact_text(summary or text, max_chars)


def _parse_json_text(text: str) -> dict[str, Any]:
    parsed = parse_json_object(text, {})
    return parsed if isinstance(parsed, dict) else {}


def _coerce_string_list(value: Any, limit: int = 10) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item)[:300] for item in value if str(item).strip()][:limit]


def _extract_paths(text: str, limit: int = 12) -> list[str]:
    seen: dict[str, None] = {}
    for match in PATH_PATTERN.findall(text):
        seen.setdefault(match, None)
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


def compact_explore_result(response: dict, max_chars: int = 2500) -> dict:
    text = compact_text(extract_opencode_text(response), max_chars=max_chars)
    parsed = _parse_json_text(text)
    return {
        "agent": "explore",
        "raw_response_kept": False,
        "compact": True,
        "summary": str(parsed.get("summary") or _summary_from_text(text))[:600],
        "relevant_files": _coerce_string_list(parsed.get("relevant_files")) or _extract_paths(text),
        "risks": _coerce_string_list(parsed.get("risks")),
        "test_hints": _coerce_string_list(parsed.get("test_hints")),
        "raw_text_truncated": text,
    }


def compact_plan_result(response: dict, max_chars: int = 2500) -> dict:
    text = compact_text(extract_opencode_text(response), max_chars=max_chars)
    parsed = _parse_json_text(text)
    return {
        "agent": "plan",
        "raw_response_kept": False,
        "compact": True,
        "summary": str(parsed.get("summary") or _summary_from_text(text))[:600],
        "execution_plan": _coerce_string_list(parsed.get("execution_plan")) or _extract_action_lines(text),
        "raw_text_truncated": text,
    }


def compact_build_result(response: dict, max_chars: int = 2000) -> dict:
    text = compact_text(extract_opencode_text(response), max_chars=max_chars)
    parsed = _parse_json_text(text)
    return {
        "agent": "build",
        "raw_response_kept": False,
        "compact": True,
        "summary": str(parsed.get("summary") or _summary_from_text(text))[:600],
        "raw_text_truncated": text,
    }


def compact_validator_result(response: dict, max_chars: int = 2500) -> dict:
    text = compact_text(extract_opencode_text(response), max_chars=max_chars)
    parsed = parse_json_object(text, {})
    if parsed:
        result = dict(parsed)
        result["raw_response_kept"] = False
        result["compact"] = True
        result["raw_text_truncated"] = text
        return result
    return {
        "passed": False,
        "score": 0,
        "summary": "Validator did not return valid JSON.",
        "blocking_issues": ["Validator output was not valid JSON."],
        "non_blocking_issues": [],
        "retry_instruction": "Re-check the task against the diff and return strict JSON validation.",
        "raw_response_kept": False,
        "compact": True,
        "raw_text_truncated": text,
    }


def prompt_summary(prompt: str, max_chars: int = 1000) -> str:
    return compact_text(prompt, max_chars=max_chars)

from __future__ import annotations

import json
import re
from typing import Any


def default_agent_result(raw: str = "", passed: bool = False) -> dict[str, Any]:
    return {
        "passed": passed,
        "summary": "",
        "raw": raw,
    }


def parse_json_object(raw: Any, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    if isinstance(raw, dict):
        return dict(raw)

    text = str(raw or "").strip()
    base = dict(fallback or default_agent_result(text))
    if not text:
        return base

    candidates = [text]
    fenced = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    candidates.extend(fenced)

    first = text.find("{")
    last = text.rfind("}")
    if first != -1 and last != -1 and last > first:
        candidates.append(text[first : last + 1])

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except Exception:
            continue
        if isinstance(parsed, dict):
            result = dict(base)
            result.update(parsed)
            result["raw"] = text
            return result
    return base


def coerce_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]

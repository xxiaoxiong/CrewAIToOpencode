from __future__ import annotations


BAD_PATTERNS = [
    "TODO",
    "FIXME",
    "HACK",
    "hack",
    "临时绕过",
    "先这样",
    "skip test",
    "it.skip",
    "describe.skip",
    "@Disabled",
    "console.log(",
    "debugger",
    "password=",
    "api_key=",
    "secret=",
]


def scan_bad_patterns(diff_text: str) -> dict:
    hits: list[str] = []
    for pattern in BAD_PATTERNS:
        if pattern in diff_text and pattern not in hits:
            hits.append(pattern)
    return {"passed": not hits, "hits": hits}

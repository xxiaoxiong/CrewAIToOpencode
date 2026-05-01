import json

from src.orchestration.context_compactor import compact_explore_result, compact_text, extract_opencode_text


def _raw_response():
    return {
        "info": {"route": "message"},
        "sessionID": "ses_123",
        "messageID": "msg_123",
        "tokens": {"input": 1000},
        "cache": {"hit": False},
        "parts": [
            {"type": "reasoning", "text": "hidden reasoning"},
            {"type": "text", "text": "Summary: inspect src/App.jsx\n- src/App.jsx\n- tests/app.test.js"},
            {"type": "snapshot", "path": "ignored"},
        ],
    }


def test_extract_opencode_text_reads_only_text_parts():
    assert extract_opencode_text(_raw_response()) == "Summary: inspect src/App.jsx\n- src/App.jsx\n- tests/app.test.js"


def test_compact_explore_result_strips_api_metadata():
    result = compact_explore_result(_raw_response(), max_chars=80)
    payload = json.dumps(result, ensure_ascii=False)

    assert "src/App.jsx" in payload
    assert len(result["raw_text_truncated"]) <= 80
    for forbidden in ["tokens", "cache", "sessionID", "messageID", "parts", "info"]:
        assert forbidden not in payload


def test_compact_text_preserves_head_and_tail_when_truncated():
    text = "a" * 80 + "\n" + "b" * 80
    compacted = compact_text(text, max_chars=60)

    assert len(compacted) <= 60
    assert "[truncated]" in compacted

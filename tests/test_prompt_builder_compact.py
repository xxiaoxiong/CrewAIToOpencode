import json

from src.orchestration.prompt_builder import build_initial_prompt


def test_build_initial_prompt_compacts_raw_opencode_response():
    raw_response = {
        "info": {"kind": "message"},
        "sessionID": "ses_123",
        "messageID": "msg_123",
        "parentID": "parent_123",
        "tokens": {"input": 2000},
        "cache": {"hit": True, "blob": "x" * 5000},
        "parts": [
            {"type": "snapshot", "text": "ignore snapshot"},
            {"type": "text", "text": "Explore summary\nRelevant file: src/App.jsx\nRisk: keep scope focused"},
        ],
    }

    prompt = build_initial_prompt(
        "build the app",
        {"denied_paths": [".env"], "prompt_limits": {"section_max_chars": 500}},
        explore_result=raw_response,
    )
    raw_json = json.dumps(raw_response, ensure_ascii=False)

    assert "[OpenCode Explore Summary]" in prompt
    assert "Explore summary" in prompt
    assert len(prompt) < len(raw_json) + 1200
    for forbidden in ["tokens", "cache", "sessionID", "messageID", "parts", "snapshot", "parentID", "raw_response"]:
        assert forbidden not in prompt

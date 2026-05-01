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
    assert "[Task Contract]" in prompt
    assert "[Repository Fact Summary]" in prompt
    assert '"task_type":' in prompt
    assert '"acceptance_criteria":' in prompt
    assert "Explore summary" in prompt
    assert len(prompt) < len(raw_json) + 1200
    for forbidden in ["tokens", "cache", "sessionID", "messageID", "parts", "snapshot", "parentID", "raw_response"]:
        assert forbidden not in prompt


def test_build_prompt_uses_task_contract_and_repo_facts_only():
    prompt = build_initial_prompt(
        "create a React + Vite dashboard",
        {
            "denied_paths": [".env"],
            "test_command": "npm test",
            "prompt_limits": {"section_max_chars": 800},
        },
        task_contract={
            "task_type": "frontend_project_creation",
            "goal": "create a React + Vite dashboard",
            "must_create_or_modify_files": ["package.json", "src/App.jsx"],
            "acceptance_criteria": ["real runnable frontend"],
            "denied_paths": [".env"],
            "validation_commands": ["npm test"],
            "final_output_requirements": ["changed files and validation"],
        },
        repo_summary={
            "repo_summary": "empty workspace ready for frontend project",
            "project_type": "frontend/javascript",
            "existing_files": [],
            "relevant_files": ["package.json", "src/App.jsx"],
            "risks": ["avoid README-only output"],
            "suggested_scope": ["create app shell"],
        },
    )

    assert '"task_type": "frontend_project_creation"' in prompt
    assert '"repo_summary": "empty workspace ready for frontend project"' in prompt
    assert len(prompt) < 5000
    for forbidden in ["tokens", "cache", "sessionID", "messageID", "parts", "raw_response"]:
        assert forbidden not in prompt

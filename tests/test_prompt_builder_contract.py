import json

from src.orchestration.prompt_builder import build_initial_prompt


def test_build_prompt_contains_contract_and_repo_facts_without_raw_response():
    raw_explore = {
        "sessionID": "ses",
        "messageID": "msg",
        "tokens": {"input": 2000},
        "cache": {"hit": True},
        "parts": [{"type": "text", "text": "Explore summary\nRelevant file: src/App.jsx"}],
    }
    prompt = build_initial_prompt(
        "create a React + Vite app",
        {"denied_paths": [".env"], "prompt_limits": {"build_max_chars": 6000, "section_max_chars": 800}},
        explore_result=raw_explore,
        task_contract={
            "task_type": "frontend_project_creation",
            "goal": "create a React + Vite app",
            "must_create_or_modify_files": ["package.json", "index.html", "src/App.jsx"],
            "acceptance_criteria": ["real runnable frontend"],
            "denied_paths": [".env"],
            "validation_commands": ["npm test"],
            "final_output_requirements": ["changed files and validation"],
        },
    )
    raw_json = json.dumps(raw_explore, ensure_ascii=False)

    assert "[Task Contract]" in prompt
    assert "[Repository Facts]" in prompt
    assert '"task_type": "frontend_project_creation"' in prompt
    assert "package.json" in prompt
    assert len(prompt) < 6000
    assert raw_json not in prompt
    for forbidden in ["tokens", "cache", "sessionID", "messageID", "parts", "raw_response"]:
        assert forbidden not in prompt

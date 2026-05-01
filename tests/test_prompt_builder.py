from src.orchestration.prompt_builder import build_initial_prompt, build_retry_prompt


def test_build_initial_prompt_contains_required_sections():
    prompt = build_initial_prompt(
        "test task",
        {
            "allowed_write_paths": ["README.md"],
            "denied_paths": [".env"],
            "test_command": "npm test",
        },
    )

    assert "[Task Goal]" in prompt
    assert "Only modify these allowed paths" not in prompt
    assert "Create or modify any project files needed" in prompt
    assert "Never modify these denied paths" in prompt
    assert "npm test" in prompt
    assert "Do not delete, skip, weaken, or bypass tests" in prompt


def test_build_initial_prompt_accepts_plan_result():
    prompt = build_initial_prompt(
        "test task",
        {"allowed_write_paths": ["README.md"], "denied_paths": [], "test_command": ""},
        {
            "summary": "plan summary",
            "execution_plan": ["edit README"],
            "opencode_instruction": "Use a small README edit.",
        },
    )

    assert "[Architect Plan]" in prompt
    assert "plan summary" in prompt
    assert "Use a small README edit." in prompt


def test_build_initial_prompt_contains_explore_and_opencode_plan():
    prompt = build_initial_prompt(
        "test task",
        {"allowed_write_paths": ["README.md"], "denied_paths": [], "test_command": "pytest"},
        {"summary": "architect"},
        explore_result={"summary": "explore found README"},
        opencode_plan={"summary": "opencode plan"},
    )

    assert "[OpenCode Explore Summary]" in prompt
    assert "explore found README" in prompt
    assert "[OpenCode Plan Summary]" in prompt
    assert "opencode plan" in prompt


def test_build_retry_prompt_contains_failure_context():
    prompt = build_retry_prompt(
        "test task",
        {"passed": False, "test": {"passed": False, "stderr": "failed"}},
        {"passed": False, "blocking_issues": ["bug"], "retry_instruction": "fix bug"},
        2,
    )

    assert "[Original Task]" in prompt
    assert "2" in prompt
    assert "failed" in prompt
    assert "bug" in prompt


def test_build_retry_prompt_contains_tester_analysis():
    prompt = build_retry_prompt(
        "test task",
        {"passed": False, "test": {"passed": False, "stderr": "failed"}},
        {"passed": False, "blocking_issues": []},
        2,
        {"failure_type": "code_issue", "retry_instruction": "fix assertion"},
    )

    assert "[Tester Analyst]" in prompt
    assert "code_issue" in prompt
    assert "fix assertion" in prompt


def test_build_retry_prompt_contains_contract_without_previous_prompt():
    prompt = build_retry_prompt(
        "test task",
        {"passed": False, "changed_files": [], "test": {"passed": False, "stderr": "failed"}},
        {"passed": False, "blocking_issues": ["missing output"], "retry_instruction": "create files"},
        2,
        task_contract={
            "task_type": "implementation",
            "goal": "test task",
            "must_create_or_modify_files": ["src/app.py"],
            "acceptance_criteria": ["files are created"],
            "denied_paths": [".env"],
            "validation_commands": ["pytest"],
            "final_output_requirements": ["summarize validation"],
        },
    )

    assert "[Task Contract]" in prompt
    assert "[Failed Acceptance Items]" in prompt
    assert "src/app.py" in prompt
    assert "previous prompt" not in prompt.lower()
    for forbidden in ["tokens", "cache", "sessionID", "messageID", "parts", "raw_response"]:
        assert forbidden not in prompt


def test_frontend_creation_prompt_requires_real_project_files():
    prompt = build_initial_prompt(
        "请创建一个 React + Vite 前端系统",
        {"allowed_write_paths": ["README.md"], "denied_paths": [".env"], "test_command": ""},
    )

    assert "Create actual runnable project files" in prompt
    assert "do not satisfy it by only writing README text" in prompt
    assert "package.json" in prompt
    assert "index.html" in prompt
    assert "src/main.jsx or src/main.tsx" in prompt
    assert "src/App.jsx or src/App.tsx" in prompt
    assert "Only modify these allowed paths" not in prompt

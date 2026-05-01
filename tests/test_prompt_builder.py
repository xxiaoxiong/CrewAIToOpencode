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
    assert "Only modify these allowed paths" in prompt
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

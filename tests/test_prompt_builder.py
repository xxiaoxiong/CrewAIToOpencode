from src.orchestration.prompt_builder import build_initial_prompt, build_retry_prompt


def test_build_initial_prompt_contains_required_sections():
    prompt = build_initial_prompt(
        "测试任务",
        {
            "allowed_write_paths": ["README.md"],
            "denied_paths": [".env"],
            "test_command": "npm test",
        },
    )

    assert "任务目标" in prompt
    assert "只允许修改" in prompt
    assert "禁止修改" in prompt
    assert "npm test" in prompt
    assert "不允许删除测试" in prompt


def test_build_retry_prompt_contains_failure_context():
    prompt = build_retry_prompt(
        "测试任务",
        {"passed": False, "test": {"passed": False, "stderr": "failed"}},
        {"passed": False, "blocking_issues": ["bug"], "retry_instruction": "fix bug"},
        2,
    )

    assert "原始任务" in prompt
    assert "第 2 轮" in prompt
    assert "failed" in prompt
    assert "bug" in prompt

from src.quality.quality_gate import run_quality_gate


def test_run_quality_gate_accepts_task_text_argument(tmp_path):
    result = run_quality_gate(
        {
            "repo_path": str(tmp_path),
            "denied_paths": [".env"],
            "test_enabled": False,
            "lint_enabled": False,
        },
        "task text",
    )

    assert "file_policy" in result

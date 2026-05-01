from src.orchestration import flow_runner


class FakeClient:
    def health(self):
        return {"healthy": True}

    def current_path(self):
        return {"directory": "demo-project"}

    def vcs(self):
        return {"branch": "master"}

    def create_session(self, title):
        return {"id": "ses_test"}

    def get_diff(self, session_id):
        return {"data": []}


def test_retry_history_keeps_prompt_summary_not_full_prompt(monkeypatch):
    config = {
        "id": "demo-project",
        "repo_path": ".",
        "max_iterations": 2,
        "post_message_wait_seconds": 0,
        "reviewer_enabled": True,
        "task_pipeline": {
            "explore_enabled": False,
            "architect_enabled": False,
            "opencode_plan_enabled": False,
            "build_enabled": True,
            "tester_enabled": True,
            "validator_enabled": True,
            "reviewer_enabled": True,
            "reporter_enabled": False,
            "max_iterations": 2,
        },
        "modes": {},
        "crewai": {"enabled": False},
        "prompt_limits": {"build_max_chars": 12000, "retry_max_chars": 8000},
    }
    monkeypatch.setattr(flow_runner, "get_project_config", lambda project_id: config)
    monkeypatch.setattr(flow_runner.OpenCodeClient, "from_project_config", lambda config: FakeClient())
    monkeypatch.setattr(flow_runner, "_write_reports", lambda report: report)
    monkeypatch.setattr(flow_runner, "opencode_build", lambda *args: {"summary": "build"})
    monkeypatch.setattr(flow_runner, "opencode_repair", lambda *args: {"summary": "repair"})

    calls = {"quality": 0}

    def fake_quality(*args, **kwargs):
        calls["quality"] += 1
        return {
            "passed": calls["quality"] == 2,
            "changed_files": ["README.md"] if calls["quality"] == 2 else [],
            "test": {"enabled": False, "passed": True},
            "lint": {"enabled": False, "passed": True},
            "file_policy": {"passed": True, "violations": []},
            "bad_patterns": {"passed": True, "hits": []},
            "diff": "",
            "git_diff_stat": "",
        }

    monkeypatch.setattr(flow_runner, "run_quality_gate", fake_quality)
    monkeypatch.setattr(
        flow_runner,
        "review_change",
        lambda task, quality: {"passed": quality["passed"], "score": 85, "blocking_issues": [] if quality["passed"] else ["retry"], "retry_instruction": "retry"},
    )
    monkeypatch.setattr(flow_runner, "opencode_validate", lambda *args: {"passed": True, "score": 90})

    report = flow_runner.run_dev_task("demo-project", "task")

    assert report["passed"] is True
    assert "prompt" not in report["retry_history"][0]
    assert "prompt_summary" in report["retry_history"][0]
    assert isinstance(report["retry_history"][0]["prompt_chars"], int)

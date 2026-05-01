from src.orchestration import flow_runner


class FakeClient:
    def health(self):
        return {"ok": True}

    def current_path(self):
        return {"path": "."}

    def vcs(self):
        return {"branch": "main"}

    def create_session(self, title):
        return {"id": "ses_test"}

    def send_message(self, session_id, text, agent):
        return {"ok": True, "session_id": session_id, "agent": agent}

    def get_diff(self, session_id):
        return {"diff": "sample"}


def test_run_dev_task_retries_until_pass(monkeypatch):
    monkeypatch.setattr(
        flow_runner,
        "get_project_config",
        lambda project_id: {
            "id": project_id,
            "repo_path": ".",
            "max_iterations": 3,
            "opencode_agent": "build",
            "reviewer_enabled": True,
            "allowed_write_paths": ["README.md"],
            "denied_paths": [],
            "test_command": "",
            "post_message_wait_seconds": 0,
        },
    )
    monkeypatch.setattr(flow_runner.OpenCodeClient, "from_project_config", lambda config: FakeClient())

    calls = {"count": 0}

    def fake_quality(config):
        calls["count"] += 1
        return {
            "passed": calls["count"] >= 2,
            "changed_files": ["README.md"] if calls["count"] >= 2 else [],
            "test": {"enabled": False, "passed": True, "cmd": ""},
            "lint": {"enabled": False, "passed": True, "cmd": ""},
            "file_policy": {"passed": True, "violations": []},
            "bad_patterns": {"passed": True, "hits": []},
            "diff": "",
            "git_diff_stat": "",
        }

    monkeypatch.setattr(flow_runner, "run_quality_gate", fake_quality)
    monkeypatch.setattr(
        flow_runner,
        "review_change",
        lambda task, quality: {
            "passed": quality["passed"],
            "score": 80,
            "blocking_issues": [] if quality["passed"] else ["No changes"],
            "non_blocking_issues": [],
            "retry_instruction": "retry",
            "raw": "fake",
        },
    )

    report = flow_runner.run_dev_task("demo-project", "task", max_iterations=3)

    assert report["passed"] is True
    assert report["iterations_used"] == 2
    assert report["session_id"] == "ses_test"

import json

from src.orchestration import flow_runner


class FakeClient:
    def health(self):
        return {"healthy": True}

    def current_path(self):
        return {"directory": "demo-project"}

    def vcs(self):
        return {"branch": "main"}

    def create_session(self, title):
        return {"id": "ses_test"}


def test_run_dev_task_report_does_not_contain_raw_opencode_response(monkeypatch):
    config = {
        "id": "demo-project",
        "repo_path": ".",
        "max_iterations": 1,
        "post_message_wait_seconds": 0,
        "reviewer_enabled": True,
        "denied_paths": [],
        "task_pipeline": {
            "explore_enabled": True,
            "architect_enabled": False,
            "opencode_plan_enabled": False,
            "build_enabled": True,
            "tester_enabled": False,
            "validator_enabled": True,
            "reviewer_enabled": True,
            "reporter_enabled": False,
            "max_iterations": 1,
        },
        "modes": {},
        "crewai": {"enabled": False},
        "prompt_limits": {"build_max_chars": 6000, "retry_max_chars": 4000, "plan_max_chars": 5000, "section_max_chars": 1800},
    }
    raw_like = {
        "sessionID": "raw_session",
        "messageID": "raw_message",
        "tokens": {"input": 1},
        "cache": {"hit": False},
        "parts": [{"type": "text", "text": "summary"}],
        "raw_response": {"bad": True},
    }

    monkeypatch.setattr(flow_runner, "get_project_config", lambda project_id: config)
    monkeypatch.setattr(flow_runner.OpenCodeClient, "from_project_config", lambda config: FakeClient())
    monkeypatch.setattr(flow_runner, "_write_reports", lambda report: report)
    monkeypatch.setattr(flow_runner, "opencode_explore", lambda *args: raw_like)
    monkeypatch.setattr(flow_runner, "opencode_build", lambda *args: raw_like)
    monkeypatch.setattr(
        flow_runner,
        "run_quality_gate",
        lambda *args: {
            "passed": True,
            "changed_files": ["README.md"],
            "test": {"enabled": False, "passed": True},
            "lint": {"enabled": False, "passed": True},
            "file_policy": {"passed": True, "violations": []},
            "bad_patterns": {"passed": True, "hits": []},
            "diff": "",
            "git_diff_stat": "",
        },
    )
    monkeypatch.setattr(flow_runner, "opencode_validate", lambda *args: {"stage": "validate", "passed": True, "score": 90, "criteria_results": [], "missing_files": [], "blocking_issues": [], "retry_instruction": ""})
    monkeypatch.setattr(flow_runner, "review_change", lambda *args: {"passed": True, "score": 90, "blocking_issues": [], "non_blocking_issues": [], "retry_instruction": ""})

    report = flow_runner.run_dev_task("demo-project", "task")
    payload = json.dumps(report, ensure_ascii=False)

    for forbidden in ["raw_response", "tokens", "cache", "sessionID", "messageID", "parts"]:
        assert forbidden not in payload

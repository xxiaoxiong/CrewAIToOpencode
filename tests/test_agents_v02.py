from src.agents.architect_agent import build_architect_plan
from src.orchestration import flow_runner


class CapturingClient:
    def __init__(self):
        self.sent_prompts = []

    def health(self):
        return {"healthy": True}

    def current_path(self):
        return {"directory": "demo-project"}

    def vcs(self):
        return {"branch": "master"}

    def create_session(self, title):
        return {"id": "ses_test"}

    def send_message(self, session_id, text, agent, timeout=None):
        self.sent_prompts.append(text)
        return {"ok": True, "agent": agent}

    def get_diff(self, session_id):
        return {"data": []}


def test_architect_agent_falls_back_when_crewai_unavailable(monkeypatch):
    monkeypatch.setattr(
        "src.agents.architect_agent._run_crewai",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("crewai unavailable")),
    )

    result = build_architect_plan(
        "task",
        {"allowed_write_paths": ["README.md"], "denied_paths": [".env"]},
        {"branch": "master"},
    )

    assert result["passed"] is True
    assert "fallback" in result["raw"].lower()
    assert result["opencode_instruction"]
    assert "Allowed paths" not in result["opencode_instruction"]
    assert not any("Only modify allowed paths" in item for item in result["constraints"])


def test_flow_runner_crewai_disabled_keeps_v01_path(monkeypatch):
    client = CapturingClient()
    monkeypatch.setattr(
        flow_runner,
        "get_project_config",
        lambda project_id: {
            "id": project_id,
            "repo_path": ".",
            "max_iterations": 1,
            "opencode_agent": "build",
            "reviewer_enabled": True,
            "post_message_wait_seconds": 0,
            "crewai": {"enabled": False},
        },
    )
    monkeypatch.setattr(flow_runner.OpenCodeClient, "from_project_config", lambda config: client)
    monkeypatch.setattr(flow_runner, "_write_reports", lambda report: report)
    monkeypatch.setattr(
        flow_runner,
        "build_architect_plan",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("architect should not run")),
    )
    monkeypatch.setattr(
        flow_runner,
        "run_quality_gate",
        lambda *args, **kwargs: {
            "passed": True,
            "changed_files": ["README.md"],
            "test": {"enabled": True, "passed": True},
            "lint": {"enabled": False, "passed": True},
            "file_policy": {"passed": True, "violations": []},
            "bad_patterns": {"passed": True, "hits": []},
            "diff": "",
            "git_diff_stat": "",
        },
    )
    monkeypatch.setattr(
        flow_runner,
        "review_change",
        lambda task, quality: {"passed": True, "score": 85, "blocking_issues": []},
    )
    monkeypatch.setattr(flow_runner, "opencode_validate", lambda *args: {"passed": True, "score": 90})

    report = flow_runner.run_dev_task("demo-project", "task")

    assert report["passed"] is True
    assert "[Architect Plan]" not in client.sent_prompts[0]


def test_flow_runner_crewai_enabled_adds_plan_and_tester_retry(monkeypatch):
    client = CapturingClient()
    monkeypatch.setattr(
        flow_runner,
        "get_project_config",
        lambda project_id: {
            "id": project_id,
            "repo_path": ".",
            "max_iterations": 2,
            "opencode_agent": "build",
            "reviewer_enabled": True,
            "post_message_wait_seconds": 0,
            "crewai": {
                "enabled": True,
                "planning_enabled": True,
                "tester_analysis_enabled": True,
                "reviewer_enabled": True,
                "reporter_enabled": True,
            },
        },
    )
    monkeypatch.setattr(flow_runner.OpenCodeClient, "from_project_config", lambda config: client)
    monkeypatch.setattr(flow_runner, "_write_reports", lambda report: report)
    monkeypatch.setattr(
        flow_runner,
        "build_architect_plan",
        lambda *args, **kwargs: {
            "passed": True,
            "summary": "architect summary",
            "affected_areas": ["README.md"],
            "execution_plan": ["edit README"],
            "constraints": [],
            "opencode_instruction": "Use the architect instruction.",
        },
    )
    calls = {"quality": 0}

    def fake_quality(*args, **kwargs):
        calls["quality"] += 1
        passed = calls["quality"] >= 2
        return {
            "passed": passed,
            "changed_files": ["README.md"] if passed else [],
            "test": {"enabled": True, "passed": passed, "stderr": "assertion failed"},
            "lint": {"enabled": False, "passed": True},
            "file_policy": {"passed": True, "violations": []},
            "bad_patterns": {"passed": True, "hits": []},
            "diff": "",
            "git_diff_stat": "",
        }

    monkeypatch.setattr(flow_runner, "run_quality_gate", fake_quality)
    monkeypatch.setattr(
        flow_runner,
        "analyze_test_failure",
        lambda *args, **kwargs: {
            "passed": False,
            "failure_type": "code_issue",
            "root_cause_summary": "assertion mismatch",
            "retry_instruction": "fix assertion",
        },
    )
    monkeypatch.setattr(
        flow_runner,
        "review_change",
        lambda task, quality, config: {
            "passed": quality["passed"],
            "score": 85,
            "blocking_issues": [] if quality["passed"] else ["test failed"],
            "retry_instruction": "retry",
        },
    )
    monkeypatch.setattr(
        flow_runner,
        "summarize_delivery",
        lambda report, config: {"passed": True, "summary": "done", "validation_summary": "ok"},
    )
    monkeypatch.setattr(flow_runner, "opencode_validate", lambda *args: {"passed": True, "score": 90})

    report = flow_runner.run_dev_task("demo-project", "task")

    assert report["passed"] is True
    assert "[Architect Plan]" in client.sent_prompts[0]
    assert "Use the architect instruction." in client.sent_prompts[0]
    assert "[Tester Analyst]" in client.sent_prompts[1]
    assert "fix assertion" in client.sent_prompts[1]
    assert report["reporter"]["summary"] == "done"

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


def _config(mode_flags=None):
    return {
        "id": "demo-project",
        "repo_path": ".",
        "max_iterations": 1,
        "post_message_wait_seconds": 0,
        "reviewer_enabled": True,
        "opencode_agents": {
            "explorer": "explore",
            "planner": "plan",
            "coder": "build",
            "repairer": "build",
        },
        "task_pipeline": {
            "explore_enabled": True,
            "architect_enabled": True,
            "opencode_plan_enabled": True,
            "build_enabled": True,
            "tester_enabled": True,
            "reviewer_enabled": True,
            "reporter_enabled": True,
            "max_iterations": 1,
        },
        "modes": {
            "quick": {
                "explore_enabled": False,
                "architect_enabled": False,
                "opencode_plan_enabled": False,
                "tester_enabled": False,
                "reviewer_enabled": True,
                "reporter_enabled": True,
            },
            "full": {
                "explore_enabled": True,
                "architect_enabled": True,
                "opencode_plan_enabled": True,
                "tester_enabled": True,
                "reviewer_enabled": True,
                "reporter_enabled": True,
            },
        },
        "crewai": {"enabled": False},
        **(mode_flags or {}),
    }


def _patch_common(monkeypatch, config):
    monkeypatch.setattr(flow_runner, "get_project_config", lambda project_id: config)
    monkeypatch.setattr(flow_runner.OpenCodeClient, "from_project_config", lambda config: FakeClient())
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
    monkeypatch.setattr(flow_runner, "summarize_delivery", lambda report, config: {"passed": True})


def test_flow_runner_quick_mode_skips_explore_architect_plan(monkeypatch):
    calls = {"explore": 0, "architect": 0, "plan": 0, "build": 0}
    _patch_common(monkeypatch, _config())
    monkeypatch.setattr(flow_runner, "opencode_explore", lambda *args: calls.__setitem__("explore", calls["explore"] + 1))
    monkeypatch.setattr(flow_runner, "build_architect_plan", lambda *args: calls.__setitem__("architect", calls["architect"] + 1))
    monkeypatch.setattr(flow_runner, "opencode_plan_task", lambda *args: calls.__setitem__("plan", calls["plan"] + 1))
    monkeypatch.setattr(
        flow_runner,
        "opencode_build",
        lambda *args: calls.__setitem__("build", calls["build"] + 1) or {"ok": True},
    )

    report = flow_runner.run_dev_task("demo-project", "task", mode="quick")

    assert report["passed"] is True
    assert calls == {"explore": 0, "architect": 0, "plan": 0, "build": 1}


def test_flow_runner_full_mode_executes_explore_architect_plan(monkeypatch):
    calls = {"explore": 0, "architect": 0, "plan": 0, "build": 0}
    _patch_common(monkeypatch, _config())
    monkeypatch.setattr(
        flow_runner,
        "opencode_explore",
        lambda *args: calls.__setitem__("explore", calls["explore"] + 1) or {"summary": "explore"},
    )
    monkeypatch.setattr(
        flow_runner,
        "build_architect_plan",
        lambda *args: calls.__setitem__("architect", calls["architect"] + 1) or {"summary": "architect"},
    )
    monkeypatch.setattr(
        flow_runner,
        "opencode_plan_task",
        lambda *args: calls.__setitem__("plan", calls["plan"] + 1) or {"summary": "plan"},
    )
    monkeypatch.setattr(
        flow_runner,
        "opencode_build",
        lambda *args: calls.__setitem__("build", calls["build"] + 1) or {"ok": True},
    )

    report = flow_runner.run_dev_task("demo-project", "task", mode="full")

    assert report["passed"] is True
    assert calls == {"explore": 1, "architect": 1, "plan": 1, "build": 1}
    assert report["explore"]["summary"] == "explore"
    assert report["architect_plan"]["summary"] == "architect"
    assert report["opencode_plan"]["summary"] == "plan"


def test_flow_runner_repairs_when_validator_fails(monkeypatch):
    calls = {"build": 0, "repair": 0, "validate": 0}
    config = _config()
    config["task_pipeline"]["max_iterations"] = 2
    _patch_common(monkeypatch, config)
    monkeypatch.setattr(flow_runner, "opencode_explore", lambda *args: {})
    monkeypatch.setattr(flow_runner, "build_architect_plan", lambda *args: {})
    monkeypatch.setattr(flow_runner, "opencode_plan_task", lambda *args: {})
    monkeypatch.setattr(
        flow_runner,
        "opencode_build",
        lambda *args: calls.__setitem__("build", calls["build"] + 1) or {"ok": True},
    )
    monkeypatch.setattr(
        flow_runner,
        "opencode_repair",
        lambda *args: calls.__setitem__("repair", calls["repair"] + 1) or {"ok": True},
    )

    def fake_validate(*args):
        calls["validate"] += 1
        return (
            {"passed": False, "blocking_issues": ["not enough"], "retry_instruction": "expand"}
            if calls["validate"] == 1
            else {"passed": True, "blocking_issues": []}
        )

    monkeypatch.setattr(flow_runner, "opencode_validate", fake_validate)

    report = flow_runner.run_dev_task("demo-project", "task", mode="full")

    assert report["passed"] is True
    assert calls["build"] == 1
    assert calls["repair"] == 1
    assert "expand" in report["retry_history"][0]["prompt"]

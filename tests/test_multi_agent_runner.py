from src.opencode import multi_agent_runner


class FakeClient:
    def __init__(self):
        self.calls = []

    def send_message(self, session_id, text, agent):
        self.calls.append((session_id, text, agent))
        return {"agent": agent, "text": text}


def test_multi_agent_runner_uses_mapped_agents(monkeypatch):
    fake = FakeClient()
    monkeypatch.setattr(
        multi_agent_runner.OpenCodeClient,
        "from_project_config",
        lambda config: fake,
    )
    config = {
        "opencode_agents": {
            "explorer": "explore",
            "planner": "plan",
            "coder": "build",
            "repairer": "build",
        }
    }

    multi_agent_runner.explore("ses", "task", config)
    multi_agent_runner.plan("ses", "task", {"x": 1}, {"y": 2}, config)
    multi_agent_runner.build("ses", "build prompt", config)
    multi_agent_runner.repair("ses", "retry prompt", config)

    assert [call[2] for call in fake.calls] == ["explore", "plan", "build", "build"]


def test_validate_uses_validator_agent_and_parses_json(monkeypatch):
    fake = FakeClient()

    def fake_send(session_id, text, agent):
        fake.calls.append((session_id, text, agent))
        return {"parts": [{"type": "text", "text": '{"passed": false, "score": 20, "blocking_issues": ["too shallow"], "retry_instruction": "expand"}'}]}

    fake.send_message = fake_send
    monkeypatch.setattr(
        multi_agent_runner.OpenCodeClient,
        "from_project_config",
        lambda config: fake,
    )

    result = multi_agent_runner.validate(
        "ses",
        "write a report",
        {"passed": True, "diff": "+short", "changed_files": ["README.md"]},
        {"opencode_agents": {"validator": "general"}},
    )

    assert fake.calls[0][2] == "general"
    assert result["passed"] is False
    assert result["blocking_issues"] == ["too shallow"]

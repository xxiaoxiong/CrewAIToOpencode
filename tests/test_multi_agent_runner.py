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

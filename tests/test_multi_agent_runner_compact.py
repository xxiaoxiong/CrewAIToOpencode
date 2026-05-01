import json

from src.opencode import multi_agent_runner


class RawResponseClient:
    def __init__(self):
        self.calls = []

    def send_message(self, session_id, text, agent, timeout=None):
        self.calls.append((session_id, text, agent, timeout))
        return {
            "info": {"route": "message"},
            "sessionID": session_id,
            "messageID": "msg_123",
            "tokens": {"input": 1000},
            "cache": {"hit": False},
            "parts": [{"type": "text", "text": "Summary\n- src/App.jsx\n- tests/app.test.js"}],
        }


def test_multi_agent_runner_returns_compact_stage_results(monkeypatch):
    fake = RawResponseClient()
    monkeypatch.setattr(multi_agent_runner.OpenCodeClient, "from_project_config", lambda config: fake)
    config = {"opencode_agents": {"explorer": "explore", "planner": "plan", "coder": "build"}}

    explore = multi_agent_runner.explore("ses", "task", config)
    plan = multi_agent_runner.plan("ses", "task", explore, {}, config)
    build = multi_agent_runner.build("ses", "build prompt", config)

    for result in [explore, plan, build]:
        payload = json.dumps(result, ensure_ascii=False)
        assert result["stage"] in {"explore", "plan", "build"}
        for forbidden in ["tokens", "cache", "sessionID", "messageID", "parts", "info"]:
            assert forbidden not in payload

    assert "sessionID" not in fake.calls[1][1]

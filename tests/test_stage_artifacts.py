import json

from src.orchestration.stage_artifacts import (
    make_build_artifact,
    make_explore_artifact,
    make_plan_artifact,
    make_validation_artifact,
)


FORBIDDEN = ["tokens", "cache", "sessionID", "messageID", "parts", "raw_response", "info", "snapshot", "metadata"]


def _raw_response(text='{"summary": "ok"}'):
    return {
        "info": {"route": "message"},
        "metadata": {"debug": True},
        "sessionID": "ses",
        "messageID": "msg",
        "tokens": {"input": 1},
        "cache": {"hit": False},
        "snapshot": {"id": "snap"},
        "parts": [{"type": "text", "text": text}],
    }


def test_artifacts_do_not_contain_opencode_transport_fields():
    artifacts = [
        make_explore_artifact(_raw_response("Repo summary\n- src/App.jsx")),
        make_plan_artifact(_raw_response('{"summary": "plan", "implementation_steps": ["edit src/App.jsx"]}')),
        make_build_artifact(_raw_response("Changed src/App.jsx")),
        make_validation_artifact(
            _raw_response('{"passed": true, "score": 90, "criteria_results": [], "blocking_issues": []}'),
            {"must_create_or_modify_files": [], "acceptance_criteria": []},
            ["src/App.jsx"],
        ),
    ]

    for artifact in artifacts:
        payload = json.dumps(artifact, ensure_ascii=False)
        for key in FORBIDDEN:
            assert key not in payload

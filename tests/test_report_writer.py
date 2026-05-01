from pathlib import Path

from src.orchestration.report_writer import write_json_report, write_markdown_report


def test_report_contains_all_v03_stage_results(tmp_path, monkeypatch):
    monkeypatch.setattr("src.orchestration.report_writer.REPORTS_DIR", tmp_path)
    report = {
        "_report_basename": "stage-report",
        "task": "task",
        "project_id": "demo-project",
        "mode": "full",
        "session_id": "ses",
        "passed": True,
        "iterations_used": 1,
        "max_iterations": 3,
        "explore": {"summary": "explore"},
        "architect_plan": {"summary": "architect", "execution_plan": ["edit"], "opencode_instruction": "do it"},
        "opencode_plan": {"summary": "plan"},
        "build": {"summary": "build"},
        "quality": {
            "passed": True,
            "changed_files": ["README.md"],
            "test": {"enabled": True, "passed": True, "cmd": "pytest"},
            "lint": {"enabled": False, "passed": True, "cmd": ""},
            "file_policy": {"passed": True, "violations": []},
            "bad_patterns": {"passed": True, "hits": []},
        },
        "tester": {"passed": True},
        "validator": {"passed": True, "score": 90, "summary": "validated", "blocking_issues": []},
        "review": {"passed": True, "score": 90, "blocking_issues": []},
        "reporter": {"summary": "done", "validation_summary": "ok"},
        "retry_history": [{"iteration": 2}],
    }

    json_path = write_json_report(report)
    md_path = write_markdown_report(report)
    markdown = Path(md_path).read_text(encoding="utf-8")

    assert Path(json_path).exists()
    assert "## OpenCode Explore" in markdown
    assert "## CrewAI Architect" in markdown
    assert "## OpenCode Plan" in markdown
    assert "## OpenCode Build" in markdown
    assert "## Quality Gate" in markdown
    assert "## CrewAI Tester" in markdown
    assert "## LLM Task Validator" in markdown
    assert "## CrewAI Reviewer" in markdown
    assert "## CrewAI Reporter" in markdown
    assert "## Retry History" in markdown


def test_report_failure_stage_and_timeout_guidance(tmp_path, monkeypatch):
    monkeypatch.setattr("src.orchestration.report_writer.REPORTS_DIR", tmp_path)
    report = {
        "_report_basename": "timeout-report",
        "task": "task",
        "project_id": "demo-project",
        "mode": "full",
        "session_id": "ses",
        "passed": False,
        "failed_stage": "opencode_plan",
        "iterations_used": 0,
        "max_iterations": 3,
        "quality": {},
        "review": {"blocking_issues": []},
        "validator": {},
        "error": "POST /session/ses/message: timed out after 300 seconds",
    }

    md_path = write_markdown_report(report)
    markdown = Path(md_path).read_text(encoding="utf-8")

    assert "- Failed stage: opencode_plan" in markdown
    assert "Timeout detected after 300 seconds" in markdown
    assert "Try standard mode or increase the relevant opencode_timeouts value" in markdown

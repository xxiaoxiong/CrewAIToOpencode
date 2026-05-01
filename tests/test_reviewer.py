from src.reviewer.crew_reviewer import _coerce_review, review_change


def test_coerce_review_accepts_valid_json():
    result = _coerce_review('{"passed": true, "score": 91, "blocking_issues": []}')

    assert result["passed"] is True
    assert result["score"] == 91


def test_coerce_review_handles_non_json():
    result = _coerce_review("not json")

    assert result["passed"] is False
    assert result["raw"] == "not json"


def test_review_change_returns_dict_without_llm(monkeypatch):
    monkeypatch.setenv("REVIEWER_DISABLE_LLM", "1")
    result = review_change("task", {"passed": True, "changed_files": ["README.md"]})

    assert isinstance(result, dict)
    assert result["passed"] is True


def test_review_change_hard_fail_cannot_be_overridden(monkeypatch):
    monkeypatch.delenv("REVIEWER_DISABLE_LLM", raising=False)

    def fake_semantic(*args, **kwargs):
        return {
            "passed": True,
            "score": 100,
            "blocking_issues": [],
            "non_blocking_issues": [],
            "retry_instruction": "",
            "raw": "fake pass",
        }

    monkeypatch.setattr("src.reviewer.crew_reviewer.run_semantic_review", fake_semantic)
    result = review_change(
        "task",
        {
            "passed": False,
            "changed_files": ["README.md"],
            "test": {"passed": False},
            "file_policy": {"passed": True},
            "bad_patterns": {"passed": True},
        },
        {"crewai": {"enabled": True, "reviewer_enabled": True}},
    )

    assert result["passed"] is False
    assert "Test failures cannot be overridden by CrewAI." in result["blocking_issues"]


def test_review_change_file_policy_and_bad_patterns_are_hard_fails(monkeypatch):
    monkeypatch.delenv("REVIEWER_DISABLE_LLM", raising=False)
    monkeypatch.setattr(
        "src.reviewer.crew_reviewer.run_semantic_review",
        lambda *args, **kwargs: {
            "passed": True,
            "score": 100,
            "blocking_issues": [],
            "non_blocking_issues": [],
            "retry_instruction": "",
        },
    )

    result = review_change(
        "task",
        {
            "passed": False,
            "changed_files": ["README.md"],
            "test": {"passed": True},
            "file_policy": {"passed": False, "violations": [{"path": ".env"}]},
            "bad_patterns": {"passed": False, "hits": ["TODO"]},
        },
        {"crewai": {"enabled": True, "reviewer_enabled": True}},
    )

    assert result["passed"] is False
    assert "File policy violations cannot be overridden by CrewAI." in result["blocking_issues"]
    assert "Dangerous pattern hits cannot be overridden by CrewAI." in result["blocking_issues"]


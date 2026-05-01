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

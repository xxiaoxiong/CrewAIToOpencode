from src.orchestration.stage_artifacts import make_validation_artifact


def _validator_response():
    return {"parts": [{"type": "text", "text": '{"passed": true, "score": 95, "criteria_results": [], "blocking_issues": []}'}]}


def test_validator_fails_when_required_package_json_missing():
    artifact = make_validation_artifact(
        _validator_response(),
        {
            "task_type": "frontend_project_creation",
            "must_create_or_modify_files": ["package.json", "index.html"],
            "acceptance_criteria": ["real runnable frontend"],
        },
        ["index.html"],
    )

    assert artifact["passed"] is False
    assert "package.json" in artifact["missing_files"]
    assert any("package.json" in issue for issue in artifact["blocking_issues"])


def test_validator_fails_readme_only_frontend_creation():
    artifact = make_validation_artifact(
        _validator_response(),
        {
            "task_type": "frontend_project_creation",
            "must_create_or_modify_files": ["package.json", "index.html", "README.md"],
            "acceptance_criteria": ["real runnable frontend"],
        },
        ["README.md"],
    )

    assert artifact["passed"] is False
    assert any("README-only" in issue for issue in artifact["blocking_issues"])

from src.quality.file_policy import check_file_policy


def test_allowed_paths_are_ignored_for_compatibility():
    result = check_file_policy(
        ["src/auth/login.ts", "tests/auth/login.test.ts", "package.json"],
        ["README.md"],
        [],
    )

    assert result["passed"] is True


def test_missing_allowed_paths_does_not_fail():
    result = check_file_policy(["package.json"], ["src/", "README.md"], [])

    assert result["passed"] is True
    assert result["violations"] == []


def test_denied_paths_are_blocking():
    result = check_file_policy([".env"], ["src/", ".env"], [".env"])

    assert result["passed"] is False
    assert result["violations"][0]["type"] == "denied"

from src.quality.file_policy import check_file_policy


def test_allowed_paths_accept_files_and_dirs():
    result = check_file_policy(
        ["src/auth/login.ts", "tests/auth/login.test.ts", "README.md"],
        ["src/", "tests/", "README.md"],
        [],
    )

    assert result["passed"] is True


def test_allowed_paths_reject_out_of_scope_file():
    result = check_file_policy(["package.json"], ["src/", "README.md"], [])

    assert result["passed"] is False
    assert result["violations"][0]["type"] == "not_allowed"


def test_denied_paths_are_blocking():
    result = check_file_policy([".env"], ["src/", ".env"], [".env"])

    assert result["passed"] is False
    assert result["violations"][0]["type"] == "denied"

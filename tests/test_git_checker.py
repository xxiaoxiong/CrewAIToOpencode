from src.quality.git_checker import extract_changed_files


def test_extract_changed_files_handles_common_statuses():
    status = " M README.md\n?? src/new.py\nA  tests/test_new.py\n"

    assert extract_changed_files(status) == ["README.md", "src/new.py", "tests/test_new.py"]


def test_extract_changed_files_uses_new_path_for_rename():
    status = "R  old/name.py -> src/name.py\n"

    assert extract_changed_files(status) == ["src/name.py"]

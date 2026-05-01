from __future__ import annotations

from src.quality.command_runner import run_cmd
from src.quality.file_policy import check_file_policy
from src.quality.git_checker import (
    extract_changed_files,
    get_git_diff,
    get_git_diff_stat,
    get_git_status,
)
from src.quality.pattern_checker import scan_bad_patterns


def run_quality_gate(project_config: dict) -> dict:
    cwd = project_config["repo_path"]
    git_status = get_git_status(cwd)
    diff = get_git_diff(cwd)
    git_diff_stat = get_git_diff_stat(cwd)
    changed_files = extract_changed_files(git_status)

    test_result = run_cmd(
        project_config.get("test_command", ""),
        cwd,
        timeout=int(project_config.get("test_timeout", 600)),
    ) if project_config.get("test_enabled", True) else run_cmd("", cwd)

    lint_result = run_cmd(
        project_config.get("lint_command", ""),
        cwd,
        timeout=int(project_config.get("lint_timeout", 600)),
    ) if project_config.get("lint_enabled", False) else run_cmd("", cwd)

    file_policy = check_file_policy(
        changed_files,
        project_config.get("allowed_write_paths", []),
        project_config.get("denied_paths", []),
    )
    bad_patterns = scan_bad_patterns(diff)

    passed = bool(changed_files)
    passed = passed and not git_status.startswith("GIT_ERROR:")
    passed = passed and (test_result["passed"] if test_result["enabled"] else True)
    passed = passed and (lint_result["passed"] if lint_result["enabled"] else True)
    passed = passed and file_policy["passed"]
    passed = passed and bad_patterns["passed"]

    return {
        "passed": passed,
        "changed_files": changed_files,
        "git_status": git_status,
        "git_diff_stat": git_diff_stat,
        "diff": diff,
        "test": test_result,
        "lint": lint_result,
        "file_policy": file_policy,
        "bad_patterns": bad_patterns,
    }

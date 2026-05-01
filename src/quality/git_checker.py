from __future__ import annotations

import subprocess
from pathlib import Path


def _run_git(args: list[str], cwd: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=str(Path(cwd)),
            text=True,
            capture_output=True,
            timeout=120,
        )
    except Exception as exc:
        return f"GIT_ERROR: {exc}"

    if completed.returncode != 0:
        return f"GIT_ERROR: {completed.stderr.strip() or completed.stdout.strip()}"
    return completed.stdout


def _normalize_path(path: str) -> str:
    return path.strip().strip('"').replace("\\", "/")


def get_git_status(cwd: str) -> str:
    return _run_git(["status", "--short"], cwd)


def get_git_diff(cwd: str) -> str:
    return _run_git(["diff"], cwd)


def get_git_diff_stat(cwd: str) -> str:
    return _run_git(["diff", "--stat"], cwd)


def extract_changed_files(status_text: str) -> list[str]:
    files: list[str] = []
    for raw_line in status_text.splitlines():
        line = raw_line.rstrip()
        if not line or line.startswith("GIT_ERROR:"):
            continue
        path_part = line[3:] if len(line) >= 4 else line
        if " -> " in path_part:
            path_part = path_part.split(" -> ", 1)[1]
        normalized = _normalize_path(path_part)
        if normalized:
            files.append(normalized)
    return files

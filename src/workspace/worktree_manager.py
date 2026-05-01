from __future__ import annotations

import subprocess
from pathlib import Path


def create_worktree(repo_path: str, worktree_base: str, branch_name: str) -> str:
    base = Path(worktree_base)
    base.mkdir(parents=True, exist_ok=True)
    target = base / branch_name.replace("/", "-")
    completed = subprocess.run(
        ["git", "worktree", "add", str(target), "-b", branch_name],
        cwd=str(Path(repo_path)),
        text=True,
        capture_output=True,
        timeout=120,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip())
    return str(target)


def remove_worktree(worktree_path: str) -> None:
    completed = subprocess.run(
        ["git", "worktree", "remove", str(Path(worktree_path))],
        text=True,
        capture_output=True,
        timeout=120,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip())

import subprocess
from pathlib import Path

from src.workspace.worktree_manager import create_worktree, remove_worktree


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, text=True, capture_output=True)


def test_create_and_remove_worktree_from_non_repo_cwd(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    (repo / "README.md").write_text("# demo\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(
        repo,
        "-c",
        "user.email=test@example.com",
        "-c",
        "user.name=Test User",
        "commit",
        "-m",
        "init",
    )

    worktree_path = create_worktree(str(repo), str(tmp_path / "worktrees"), "codex/test-agent")

    assert Path(worktree_path).exists()
    remove_worktree(worktree_path)
    assert not Path(worktree_path).exists()

from __future__ import annotations

import subprocess
from pathlib import Path


def _tail(text: str, limit: int = 8000) -> str:
    return text[-limit:] if len(text) > limit else text


def run_cmd(cmd: str, cwd: str, timeout: int = 600) -> dict:
    if not cmd or not cmd.strip():
        return {
            "enabled": False,
            "passed": True,
            "cmd": cmd,
            "stdout": "",
            "stderr": "",
            "returncode": 0,
        }

    try:
        completed = subprocess.run(
            cmd,
            cwd=str(Path(cwd)),
            shell=True,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        return {
            "enabled": True,
            "passed": completed.returncode == 0,
            "cmd": cmd,
            "stdout": _tail(completed.stdout),
            "stderr": _tail(completed.stderr),
            "returncode": completed.returncode,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "enabled": True,
            "passed": False,
            "cmd": cmd,
            "stdout": _tail(exc.stdout or ""),
            "stderr": _tail((exc.stderr or "") + f"\nCommand timed out after {timeout}s"),
            "returncode": -1,
        }
    except Exception as exc:
        return {
            "enabled": True,
            "passed": False,
            "cmd": cmd,
            "stdout": "",
            "stderr": str(exc),
            "returncode": -1,
        }

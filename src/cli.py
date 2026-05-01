from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

from src.config_loader import get_project_config
from src.config_loader import get_effective_pipeline


def _configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


def _read_task(args: argparse.Namespace) -> str:
    if args.task:
        return args.task
    if args.task_file:
        return Path(args.task_file).read_text(encoding="utf-8").strip()
    raise ValueError("either --task or --task-file is required")


def _print_check(name: str, passed: bool, payload: Any) -> None:
    status = "ok" if passed else "failed"
    print(f"{name} {status}")
    print(json.dumps(payload, ensure_ascii=False, default=str)[:1200])


def check_opencode(project_id: str, send_message: bool = False) -> int:
    from src.opencode.client import OpenCodeClient
    from src.orchestration.flow_runner import _session_id

    config = get_project_config(project_id)
    client = OpenCodeClient.from_project_config(config)
    failures = 0
    checks: list[tuple[str, Callable[[], dict[str, Any]]]] = [
        ("health", client.health),
        ("path", client.current_path),
        ("vcs", client.vcs),
        ("agents", client.agents),
        ("file_status", client.file_status),
    ]
    for name, fn in checks:
        try:
            _print_check(name, True, fn())
        except Exception as exc:
            failures += 1
            _print_check(name, False, {"error": str(exc)})

    session_id = ""
    try:
        session = client.create_session("CrewAIToOpencode interface check")
        session_id = _session_id(session)
        _print_check("create_session", True, session)
    except Exception as exc:
        failures += 1
        _print_check("create_session", False, {"error": str(exc)})

    if session_id:
        session_checks: list[tuple[str, Callable[[], dict[str, Any]]]] = [
            ("list_messages", lambda: client.list_messages(session_id)),
            ("get_diff", lambda: client.get_diff(session_id)),
        ]
        if send_message:
            session_checks.append(
                (
                    "send_message",
                    lambda: client.send_message(
                        session_id,
                        "Interface connectivity check only. Do not edit files. Reply briefly.",
                        config.get("opencode_agent", "build"),
                    ),
                )
            )
        session_checks.append(("abort", lambda: client.abort(session_id)))

        for name, fn in session_checks:
            try:
                _print_check(name, True, fn())
            except Exception as exc:
                failures += 1
                _print_check(name, False, {"error": str(exc)})

    return 1 if failures else 0


def doctor(project_id: str) -> int:
    failures = 0
    try:
        config = get_project_config(project_id)
        _print_check("config", True, {"project_id": project_id, "repo_path": config.get("repo_path")})
    except Exception as exc:
        _print_check("config", False, {"error": str(exc)})
        return 1

    try:
        import crewai

        _print_check("crewai", True, {"version": getattr(crewai, "__version__", "unknown")})
    except Exception as exc:
        failures += 1
        _print_check("crewai", False, {"error": str(exc)})

    failures += check_opencode(project_id)
    return 1 if failures else 0


def capabilities(project_id: str) -> int:
    config = get_project_config(project_id)
    payload = {
        "positioning": "personal local CrewAI + OpenCode multi-role programming orchestrator",
        "opencode_base_url": config.get("opencode_base_url"),
        "opencode_agents": config.get("opencode_agents", {}),
        "task_pipeline": config.get("task_pipeline", {}),
        "modes": {
            name: get_effective_pipeline(config, name)
            for name in sorted((config.get("modes", {}) or {}).keys())
        },
        "crewai": {
            "enabled": (config.get("crewai", {}) or {}).get("enabled", False),
            "mode": (config.get("crewai", {}) or {}).get("mode", ""),
            "agents": (config.get("crewai", {}) or {}).get("agents", {}),
        },
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run an OpenCode-backed AI development task.")
    parser.add_argument("--project", default="demo-project", help="Project ID from config/projects.yaml")
    parser.add_argument("--mode", choices=["quick", "standard", "deep", "full"], help="Personal local task pipeline mode")
    parser.add_argument("--task", help="Task text")
    parser.add_argument("--task-file", help="Path to a UTF-8 task file")
    parser.add_argument("--max-iterations", type=int, help="Maximum retry iterations")
    parser.add_argument("--doctor", action="store_true", help="Check local config, CrewAI import, and OpenCode 4096")
    parser.add_argument("--capabilities", action="store_true", help="Print local project modes and agent capabilities")
    parser.add_argument("--check-opencode", action="store_true", help="Check OpenCode health/path/vcs/agents")
    parser.add_argument(
        "--check-opencode-send-message",
        action="store_true",
        help="Also send a real OpenCode message during --check-opencode.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    _configure_stdio()
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.check_opencode:
            return check_opencode(args.project, send_message=args.check_opencode_send_message)
        if args.doctor:
            return doctor(args.project)
        if args.capabilities:
            return capabilities(args.project)

        task_text = _read_task(args)
        from src.orchestration.flow_runner import run_dev_task

        report = run_dev_task(args.project, task_text, args.max_iterations, mode=args.mode, progress=print)
        print(f"report_json: {report.get('report_json', '')}")
        print(f"report_md: {report.get('report_md', '')}")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report.get("passed") else 1
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

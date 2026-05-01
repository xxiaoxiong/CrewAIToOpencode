from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from src.settings import CONFIG_PATH, ROOT_DIR


DEFAULT_CREWAI_CONFIG: dict[str, Any] = {
    "enabled": False,
    "mode": "hybrid_planning_review",
    "planning_enabled": True,
    "tester_analysis_enabled": True,
    "reviewer_enabled": True,
    "reporter_enabled": True,
    "llm": {
        "model": "",
        "base_url": "",
        "api_key": "",
        "temperature": 0,
    },
    "agents": {
        "architect": {"role": "Software architect"},
        "tester": {"role": "Test failure analyst"},
        "reviewer": {"role": "Senior code reviewer"},
        "reporter": {"role": "Delivery reporter"},
    },
}


def _resolve_repo_path(value: str | None) -> str:
    raw = value or "."
    path = Path(raw)
    if not path.is_absolute():
        path = (ROOT_DIR / path).resolve()
    return str(path)


def load_projects_config(path: str = str(CONFIG_PATH)) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.is_absolute():
        config_path = (ROOT_DIR / config_path).resolve()
    if not config_path.exists():
        raise FileNotFoundError(f"projects config not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    if "projects" not in data or not isinstance(data["projects"], dict):
        raise ValueError("projects config must contain a 'projects' mapping")
    return data


def get_project_config(project_id: str) -> dict[str, Any]:
    data = load_projects_config()
    projects = data["projects"]
    if project_id not in projects:
        raise KeyError(f"project not found: {project_id}")

    config = dict(projects[project_id] or {})
    config["id"] = project_id
    config["repo_path"] = _resolve_repo_path(config.get("repo_path"))
    config.setdefault("allowed_write_paths", [])
    config.setdefault("denied_paths", [])
    config.setdefault("max_iterations", 3)
    config.setdefault("reviewer_enabled", True)
    config.setdefault("lint_enabled", False)
    config.setdefault("test_enabled", True)
    config.setdefault("opencode_agent", "build")
    crewai = dict(DEFAULT_CREWAI_CONFIG)
    configured_crewai = config.get("crewai", {}) or {}
    crewai.update({key: value for key, value in configured_crewai.items() if key not in {"llm", "agents"}})
    crewai["llm"] = {**DEFAULT_CREWAI_CONFIG["llm"], **(configured_crewai.get("llm", {}) or {})}
    configured_agents = configured_crewai.get("agents", {}) or {}
    crewai["agents"] = {
        name: {**defaults, **(configured_agents.get(name, {}) or {})}
        for name, defaults in DEFAULT_CREWAI_CONFIG["agents"].items()
    }
    config["crewai"] = crewai
    return config

from __future__ import annotations

from copy import deepcopy
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

DEFAULT_OPENCODE_AGENTS: dict[str, str] = {
    "explorer": "explore",
    "planner": "plan",
    "coder": "build",
    "repairer": "build",
    "validator": "general",
    "general": "general",
}

DEFAULT_DENIED_PATHS: list[str] = [
    ".git/",
    "node_modules/",
    ".env",
    ".env.local",
    "dist/",
    "build/",
]

DEFAULT_OPENCODE_TIMEOUTS: dict[str, int] = {
    "default": 600,
    "explore": 180,
    "plan": 300,
    "build": 900,
    "repair": 900,
    "validate": 300,
}

DEFAULT_PROMPT_LIMITS: dict[str, int] = {
    "build_max_chars": 12000,
    "retry_max_chars": 8000,
    "plan_max_chars": 8000,
    "section_max_chars": 2500,
}

DEFAULT_TASK_PIPELINE: dict[str, Any] = {
    "explore_enabled": True,
    "architect_enabled": True,
    "opencode_plan_enabled": False,
    "build_enabled": True,
    "tester_enabled": True,
    "validator_enabled": True,
    "reviewer_enabled": True,
    "reporter_enabled": True,
    "max_iterations": 3,
}

DEFAULT_MODES: dict[str, dict[str, Any]] = {
    "quick": {
        "explore_enabled": False,
        "architect_enabled": False,
        "opencode_plan_enabled": False,
        "tester_enabled": False,
        "validator_enabled": True,
        "reviewer_enabled": True,
        "reporter_enabled": True,
    },
    "standard": {
        "explore_enabled": True,
        "architect_enabled": True,
        "opencode_plan_enabled": False,
        "tester_enabled": True,
        "validator_enabled": True,
        "reviewer_enabled": True,
        "reporter_enabled": True,
    },
    "full": {
        "explore_enabled": True,
        "architect_enabled": True,
        "opencode_plan_enabled": True,
        "tester_enabled": True,
        "validator_enabled": True,
        "reviewer_enabled": True,
        "reporter_enabled": True,
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
    config["denied_paths"] = config.get("denied_paths") or list(DEFAULT_DENIED_PATHS)
    config.setdefault("max_iterations", 3)
    config.setdefault("reviewer_enabled", True)
    config.setdefault("lint_enabled", False)
    config.setdefault("test_enabled", True)
    config.setdefault("opencode_agent", "build")
    config["opencode_agents"] = {**DEFAULT_OPENCODE_AGENTS, **(config.get("opencode_agents", {}) or {})}
    config["opencode_timeouts"] = {**DEFAULT_OPENCODE_TIMEOUTS, **(config.get("opencode_timeouts", {}) or {})}
    config["prompt_limits"] = {**DEFAULT_PROMPT_LIMITS, **(config.get("prompt_limits", {}) or {})}
    config["task_pipeline"] = {**DEFAULT_TASK_PIPELINE, **(config.get("task_pipeline", {}) or {})}
    configured_modes = config.get("modes", {}) or {}
    config["modes"] = {
        name: {**defaults, **(configured_modes.get(name, {}) or {})}
        for name, defaults in DEFAULT_MODES.items()
    }

    crewai = deepcopy(DEFAULT_CREWAI_CONFIG)
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


def get_effective_pipeline(project_config: dict[str, Any], mode: str | None = None) -> dict[str, Any]:
    pipeline = {**DEFAULT_TASK_PIPELINE, **(project_config.get("task_pipeline", {}) or {})}
    selected_mode = mode or str(project_config.get("mode", "") or "")
    if selected_mode:
        modes = project_config.get("modes", {}) or {}
        if selected_mode not in modes:
            raise ValueError(f"unknown mode: {selected_mode}")
        pipeline.update(modes[selected_mode] or {})
    pipeline["mode"] = selected_mode or "custom"
    return pipeline

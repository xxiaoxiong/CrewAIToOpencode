from __future__ import annotations

import os
from typing import Any


def _env_or_config(env_name: str, config: dict[str, Any], key: str, default: str = "") -> str:
    value = os.getenv(env_name)
    if value is not None:
        return value
    configured = config.get(key, default)
    return "" if configured is None else str(configured)


def _first_env_or_config(env_names: list[str], config: dict[str, Any], key: str, default: str = "") -> str:
    for env_name in env_names:
        value = os.getenv(env_name)
        if value is not None:
            return value
    configured = config.get(key, default)
    return "" if configured is None else str(configured)


def get_llm_settings(project_config: dict[str, Any]) -> dict[str, Any]:
    crewai_config = project_config.get("crewai", {}) or {}
    llm_config = crewai_config.get("llm", {}) or {}
    temperature = _env_or_config("LLM_TEMPERATURE", llm_config, "temperature", "0")
    try:
        temperature_value: float | int = float(temperature)
    except ValueError:
        temperature_value = 0

    return {
        "model": _first_env_or_config(["LLM_MODEL", "CLAUDE_MODEL"], llm_config, "model", ""),
        "base_url": _first_env_or_config(["LLM_BASE_URL", "CLAUDE_BASE_URL"], llm_config, "base_url", ""),
        "api_key": _first_env_or_config(["LLM_API_KEY", "CLAUDE_API_KEY", "ANTHROPIC_API_KEY"], llm_config, "api_key", ""),
        "temperature": temperature_value,
    }


def create_llm(project_config: dict[str, Any]):
    try:
        from crewai import LLM
    except Exception as exc:  # pragma: no cover - depends on optional package
        raise RuntimeError("crewai is required to create a CrewAI LLM") from exc

    settings = get_llm_settings(project_config)
    if not settings["model"]:
        raise RuntimeError("LLM_MODEL or crewai.llm.model is required")
    if not settings["api_key"]:
        raise RuntimeError("LLM_API_KEY, CLAUDE_API_KEY, ANTHROPIC_API_KEY, or crewai.llm.api_key is required")

    kwargs: dict[str, Any] = {
        "model": settings["model"],
        "temperature": settings["temperature"],
    }
    if settings["base_url"]:
        kwargs["base_url"] = settings["base_url"]
    if settings["api_key"]:
        kwargs["api_key"] = settings["api_key"]
    return LLM(**kwargs)

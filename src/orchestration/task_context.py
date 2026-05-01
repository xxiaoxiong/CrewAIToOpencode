from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TaskContext:
    project_id: str
    task_text: str
    session_id: str = ""
    mode: str = "custom"
    explore_result: dict[str, Any] = field(default_factory=dict)
    architect_plan: dict[str, Any] = field(default_factory=dict)
    opencode_plan: dict[str, Any] = field(default_factory=dict)
    build_result: dict[str, Any] = field(default_factory=dict)
    quality_result: dict[str, Any] = field(default_factory=dict)
    tester_result: dict[str, Any] = field(default_factory=dict)
    reviewer_result: dict[str, Any] = field(default_factory=dict)
    reporter_result: dict[str, Any] = field(default_factory=dict)
    iteration: int = 0
    passed: bool = False

"""
LLM Orchestrator Agent - 任务分析和执行策略生成
"""
from __future__ import annotations

import json
import os
from typing import Any

from .llm_factory import create_llm


def plan_orchestration(
    task_text: str,
    project_config: dict[str, Any],
    repo_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    使用 LLM 分析任务，生成执行策略。

    Args:
        task_text: 用户任务描述
        project_config: 项目配置
        repo_summary: 仓库摘要（可选）

    Returns:
        {
            "mode": "llm" | "fallback",
            "passed": bool,
            "task_type": str,
            "complexity": "low" | "medium" | "high",
            "recommended_mode": "quick" | "standard" | "full",
            "should_explore": bool,
            "should_use_opencode_plan": bool,
            "should_require_tests": bool,
            "risk_level": "low" | "medium" | "high",
            "reasoning_summary": str,
            "task_contract_hints": {
                "must_create_or_modify_files": list[str],
                "acceptance_criteria": list[str],
                "validation_commands": list[str]
            },
            "execution_strategy": list[str],
            "failure_policy": {
                "max_iterations": int,
                "retry_focus": str
            }
        }
    """
    # Check if LLM is disabled
    if os.getenv("CREWAI_DISABLE_LLM", "").lower() in {"1", "true", "yes"}:
        return _fallback_orchestration(task_text, repo_summary)

    # Check orchestration_mode
    crewai_config = project_config.get("crewai", {}) or {}
    orchestration_mode = crewai_config.get("orchestration_mode", "hybrid")

    try:
        llm = create_llm(project_config)
        result = _llm_orchestration(task_text, repo_summary, llm)
        result["mode"] = "llm"
        return result
    except Exception as e:
        # intelligent 模式下，LLM 失败必须抛出异常
        if orchestration_mode == "intelligent":
            raise RuntimeError(f"Orchestrator LLM failed in intelligent mode: {e}") from e

        # hybrid 模式下，LLM 失败可以 fallback
        return _fallback_orchestration(task_text, repo_summary)


def _llm_orchestration(
    task_text: str,
    repo_summary: dict[str, Any] | None,
    llm: Any,
) -> dict[str, Any]:
    """使用 LLM 进行任务编排分析"""
    from crewai import Agent, Crew, Task

    # 构建上下文
    context = f"Task: {task_text}\n\n"
    if repo_summary:
        context += f"Repository summary:\n{json.dumps(repo_summary, indent=2, ensure_ascii=False)}\n\n"

    # 创建 Orchestrator Agent
    agent = Agent(
        role="Task Orchestrator and Strategy Planner",
        goal="Analyze the task and generate an optimal execution strategy",
        backstory=(
            "You are an expert at analyzing software development tasks. "
            "You understand task complexity, risk levels, and can recommend "
            "the best execution strategy for each task."
        ),
        llm=llm,
        verbose=False,
    )

    # 创建任务
    task = Task(
        description=(
            f"{context}"
            "Analyze this task and provide:\n"
            "1. Task type (create_frontend_project, bugfix, refactor, test_generation, documentation, implementation)\n"
            "2. Complexity level (low, medium, high)\n"
            "3. Recommended execution mode (quick, standard, full)\n"
            "4. Whether to explore the repository first\n"
            "5. Whether to use OpenCode plan phase\n"
            "6. Whether tests are required\n"
            "7. Risk level (low, medium, high)\n"
            "8. Reasoning summary\n"
            "9. Task contract hints (files to create/modify, acceptance criteria, validation commands)\n"
            "10. Execution strategy (step-by-step plan)\n"
            "11. Failure policy (max iterations, retry focus)\n\n"
            "Output ONLY valid JSON in this exact format:\n"
            "{\n"
            '  "task_type": "create_frontend_project",\n'
            '  "complexity": "high",\n'
            '  "recommended_mode": "standard",\n'
            '  "should_explore": true,\n'
            '  "should_use_opencode_plan": false,\n'
            '  "should_require_tests": true,\n'
            '  "risk_level": "medium",\n'
            '  "reasoning_summary": "This is a complete frontend project creation...",\n'
            '  "task_contract_hints": {\n'
            '    "must_create_or_modify_files": ["package.json", "src/App.tsx"],\n'
            '    "acceptance_criteria": ["Project must be runnable", "Must have tests"],\n'
            '    "validation_commands": ["npm test", "npm run build"]\n'
            '  },\n'
            '  "execution_strategy": ["Step 1", "Step 2"],\n'
            '  "failure_policy": {\n'
            '    "max_iterations": 3,\n'
            '    "retry_focus": "only failed acceptance criteria"\n'
            '  }\n'
            "}"
        ),
        expected_output="Valid JSON object with orchestration plan",
        agent=agent,
    )

    # 执行
    crew = Crew(agents=[agent], tasks=[task], verbose=False)
    result = crew.kickoff()

    # 解析结果
    try:
        result_text = str(result.raw) if hasattr(result, "raw") else str(result)
        # 尝试提取 JSON
        result_text = result_text.strip()
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()

        parsed = json.loads(result_text)

        # 规范化字段
        return {
            "passed": True,
            "task_type": parsed.get("task_type", "implementation"),
            "complexity": parsed.get("complexity", "medium"),
            "recommended_mode": parsed.get("recommended_mode", "standard"),
            "should_explore": parsed.get("should_explore", True),
            "should_use_opencode_plan": parsed.get("should_use_opencode_plan", False),
            "should_require_tests": parsed.get("should_require_tests", True),
            "risk_level": parsed.get("risk_level", "medium"),
            "reasoning_summary": parsed.get("reasoning_summary", ""),
            "task_contract_hints": parsed.get("task_contract_hints", {}),
            "execution_strategy": parsed.get("execution_strategy", []),
            "failure_policy": parsed.get("failure_policy", {"max_iterations": 3, "retry_focus": "only failed acceptance criteria"}),
        }
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        # JSON 解析失败，返回 fallback
        raise RuntimeError(f"Failed to parse orchestrator LLM output: {e}") from e


def _fallback_orchestration(
    task_text: str,
    repo_summary: dict[str, Any] | None,
) -> dict[str, Any]:
    """确定性 fallback 编排策略"""
    task_lower = task_text.lower()

    # 推断任务类型
    if any(keyword in task_lower for keyword in ["创建", "create", "new project", "新项目", "frontend", "前端项目"]):
        task_type = "create_frontend_project"
        complexity = "high"
        should_require_tests = True
    elif any(keyword in task_lower for keyword in ["bug", "fix", "修复", "问题"]):
        task_type = "bugfix"
        complexity = "medium"
        should_require_tests = True
    elif any(keyword in task_lower for keyword in ["refactor", "重构", "优化"]):
        task_type = "refactor"
        complexity = "medium"
        should_require_tests = True
    elif any(keyword in task_lower for keyword in ["test", "测试"]):
        task_type = "test_generation"
        complexity = "low"
        should_require_tests = True
    elif any(keyword in task_lower for keyword in ["doc", "文档", "readme"]):
        task_type = "documentation"
        complexity = "low"
        should_require_tests = False
    else:
        task_type = "implementation"
        complexity = "medium"
        should_require_tests = True

    return {
        "mode": "fallback",
        "passed": True,
        "task_type": task_type,
        "complexity": complexity,
        "recommended_mode": "standard",
        "should_explore": True,
        "should_use_opencode_plan": False,
        "should_require_tests": should_require_tests,
        "risk_level": "medium",
        "reasoning_summary": f"Fallback orchestration: inferred task type as {task_type}",
        "task_contract_hints": {
            "must_create_or_modify_files": [],
            "acceptance_criteria": [],
            "validation_commands": []
        },
        "execution_strategy": [
            "Explore repository structure",
            "Generate architecture plan",
            "Execute build with OpenCode",
            "Run quality gate",
            "Validate against task contract",
            "Review changes"
        ],
        "failure_policy": {
            "max_iterations": 3,
            "retry_focus": "only failed acceptance criteria"
        }
    }

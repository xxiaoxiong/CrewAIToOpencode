from __future__ import annotations

import json
import os
from typing import Any

from src.orchestration.stage_artifacts import compact_text, sanitize_stage_value


CONTRACT_KEYS = [
    "task_type",
    "goal",
    "must_create_or_modify_files",
    "acceptance_criteria",
    "denied_paths",
    "validation_commands",
    "final_output_requirements",
]


def _string_list(value: Any, limit: int = 20) -> list[str]:
    if not isinstance(value, list):
        return []
    results: list[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            results.append(text[:300])
        if len(results) >= limit:
            break
    return results


def _dedupe(values: list[str], limit: int = 20) -> list[str]:
    seen: dict[str, None] = {}
    for value in values:
        text = str(value).strip()
        if text:
            seen.setdefault(text, None)
        if len(seen) >= limit:
            break
    return list(seen)


def _infer_task_type(task_text: str, repo_summary: dict[str, Any]) -> str:
    lowered = task_text.lower()
    project_type = str(repo_summary.get("project_type", "")).lower()
    creation_terms = [
        "create",
        "build",
        "scaffold",
        "from scratch",
        "new project",
        "创建",
        "新建",
        "搭建",
    ]
    frontend_terms = [
        "frontend",
        "front-end",
        "react",
        "vite",
        "website",
        "web app",
        "页面",
        "前端",
    ]
    if any(term in lowered for term in creation_terms) and (
        any(term in lowered for term in frontend_terms) or "frontend" in project_type or "javascript" in project_type
    ):
        return "frontend_project_creation"
    if any(term in lowered for term in ["fix", "bug", "failing", "error", "修复", "报错"]):
        return "bugfix"
    if any(term in lowered for term in ["test", "pytest", "coverage", "测试"]):
        return "test_change"
    if any(term in lowered for term in ["refactor", "重构"]):
        return "refactor"
    if any(term in lowered for term in ["readme", "docs", "documentation", "文档"]):
        return "documentation"
    return "implementation"


def _default_files(task_type: str, repo_summary: dict[str, Any], architect_plan: dict[str, Any] | None) -> list[str]:
    files: list[str] = []
    if task_type == "frontend_project_creation":
        files.extend(
            [
                "package.json",
                "index.html",
                "src/main.jsx or src/main.tsx",
                "src/App.jsx or src/App.tsx",
                "src/App.css or src/styles.css",
                "README.md",
            ]
        )
    files.extend(_string_list(repo_summary.get("relevant_files"), limit=12))
    files.extend(_string_list((architect_plan or {}).get("affected_areas"), limit=12))
    return _dedupe(files)


def _validation_commands(project_config: dict[str, Any]) -> list[str]:
    commands: list[str] = []
    test_command = str(project_config.get("test_command", "") or "").strip()
    lint_command = str(project_config.get("lint_command", "") or "").strip()
    if test_command:
        commands.append(test_command)
    if lint_command:
        commands.append(lint_command)
    return commands


def build_task_contract(
    task_text: str,
    project_config: dict[str, Any],
    repo_summary: dict[str, Any] | None = None,
    architect_plan: dict[str, Any] | None = None,
    opencode_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    repo_summary = sanitize_stage_value(repo_summary or {})
    architect_plan = sanitize_stage_value(architect_plan or {})
    opencode_plan = sanitize_stage_value(opencode_plan or {})
    task_type = _infer_task_type(task_text, repo_summary)
    validation_commands = _validation_commands(project_config)

    acceptance = [
        "The implementation satisfies the user's original task.",
        "Only project files needed for the task are created or modified.",
        "Denied paths remain untouched.",
        "Configured validation commands pass, or any skipped validation is clearly explained.",
        "No tests are deleted, skipped, weakened, or bypassed to force a pass.",
    ]
    if task_type == "frontend_project_creation":
        acceptance.append("A real runnable frontend project is created; README-only output is not sufficient.")
    if architect_plan.get("summary"):
        acceptance.append(f"Architect summary: {str(architect_plan.get('summary'))[:300]}")
    if architect_plan.get("opencode_instruction"):
        acceptance.append(f"Architect instruction: {str(architect_plan.get('opencode_instruction'))[:300]}")
    if opencode_plan.get("summary"):
        acceptance.append(f"OpenCode plan summary: {str(opencode_plan.get('summary'))[:300]}")
    for item in _string_list(architect_plan.get("execution_plan"), limit=4):
        acceptance.append(f"Architect guidance considered: {item}")
    for item in _string_list(opencode_plan.get("implementation_steps") or opencode_plan.get("execution_plan"), limit=4):
        acceptance.append(f"OpenCode plan guidance considered: {item}")

    contract = {
        "task_type": task_type,
        "goal": compact_text(task_text, max_chars=1000),
        "must_create_or_modify_files": _default_files(task_type, repo_summary, architect_plan),
        "acceptance_criteria": _dedupe(acceptance, limit=16),
        "denied_paths": _string_list(project_config.get("denied_paths", []), limit=30),
        "validation_commands": validation_commands,
        "final_output_requirements": [
            "Summarize changed files.",
            "Summarize the implementation rationale.",
            "Report validation commands and results.",
            "Keep the final response concise and factual.",
        ],
    }
    return {key: contract[key] for key in CONTRACT_KEYS}


def compact_task_contract(contract: dict[str, Any] | None) -> dict[str, Any]:
    source = sanitize_stage_value(contract or {})
    return {
        "task_type": str(source.get("task_type", "implementation") or "implementation"),
        "goal": compact_text(str(source.get("goal", "") or ""), max_chars=1000),
        "must_create_or_modify_files": _string_list(source.get("must_create_or_modify_files"), limit=20),
        "acceptance_criteria": _string_list(source.get("acceptance_criteria"), limit=20),
        "denied_paths": _string_list(source.get("denied_paths"), limit=30),
        "validation_commands": _string_list(source.get("validation_commands"), limit=10),
        "final_output_requirements": _string_list(source.get("final_output_requirements"), limit=10),
    }


def build_llm_enhanced_task_contract(
    task_text: str,
    project_config: dict[str, Any],
    repo_summary: dict[str, Any],
    orchestrator_plan: dict[str, Any],
    architect_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    使用 LLM 和 Orchestrator 分析结果生成增强的 Task Contract。

    Args:
        task_text: 用户任务描述
        project_config: 项目配置
        repo_summary: 仓库摘要
        orchestrator_plan: Orchestrator 分析结果
        architect_plan: 架构师计划（可选）

    Returns:
        增强的 Task Contract
    """
    # Check if LLM is disabled
    if os.getenv("CREWAI_DISABLE_LLM", "").lower() in {"1", "true", "yes"}:
        return build_task_contract(task_text, project_config, repo_summary, architect_plan)

    try:
        from src.agents.llm_factory import create_llm
        from crewai import Agent, Crew, Task

        llm = create_llm(project_config)

        # 构建上下文
        context = f"Task: {task_text}\n\n"
        context += f"Orchestrator Analysis:\n{json.dumps(orchestrator_plan, indent=2, ensure_ascii=False)}\n\n"
        if repo_summary:
            context += f"Repository Summary:\n{json.dumps(repo_summary, indent=2, ensure_ascii=False)}\n\n"
        if architect_plan:
            context += f"Architect Plan:\n{json.dumps(architect_plan, indent=2, ensure_ascii=False)}\n\n"

        # 创建 Agent
        agent = Agent(
            role="Task Contract Specialist",
            goal="Generate precise task contracts with accurate file lists and acceptance criteria",
            backstory=(
                "You are an expert at creating detailed task contracts. "
                "You understand what files need to be created or modified, "
                "and what acceptance criteria should be checked."
            ),
            llm=llm,
            verbose=False,
        )

        # 创建任务
        task = Task(
            description=(
                f"{context}"
                "Based on the task, orchestrator analysis, repository summary, and architect plan, "
                "generate a precise Task Contract.\n\n"
                "Output ONLY valid JSON in this exact format:\n"
                "{\n"
                '  "task_type": "create_frontend_project | bugfix | refactor | test_generation | documentation | implementation",\n'
                '  "goal": "Clear task goal",\n'
                '  "must_create_or_modify_files": ["file1.js", "file2.tsx"],\n'
                '  "acceptance_criteria": ["Criterion 1", "Criterion 2"],\n'
                '  "validation_commands": ["npm test", "npm run build"]\n'
                "}"
            ),
            expected_output="Valid JSON object with task contract",
            agent=agent,
        )

        # 执行
        crew = Crew(agents=[agent], tasks=[task], verbose=False)
        result = crew.kickoff()

        # 解析结果
        result_text = str(result.raw) if hasattr(result, "raw") else str(result)
        result_text = result_text.strip()
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()

        parsed = json.loads(result_text)

        # 合并 LLM 结果和确定性规则
        base_contract = build_task_contract(task_text, project_config, repo_summary, architect_plan)

        # 使用 LLM 增强的字段
        enhanced_contract = {
            "task_type": parsed.get("task_type", base_contract["task_type"]),
            "goal": parsed.get("goal", base_contract["goal"]),
            "must_create_or_modify_files": _dedupe(
                parsed.get("must_create_or_modify_files", []) + base_contract["must_create_or_modify_files"],
                limit=20
            ),
            "acceptance_criteria": _dedupe(
                parsed.get("acceptance_criteria", []) + base_contract["acceptance_criteria"],
                limit=16
            ),
            "denied_paths": base_contract["denied_paths"],  # 保持确定性
            "validation_commands": parsed.get("validation_commands", base_contract["validation_commands"]),
            "final_output_requirements": base_contract["final_output_requirements"],  # 保持确定性
        }

        return {key: enhanced_contract[key] for key in CONTRACT_KEYS}

    except Exception:
        # LLM 失败，fallback 到确定性 contract
        return build_task_contract(task_text, project_config, repo_summary, architect_plan)

"""
测试 Orchestrator Agent
"""
import os
from unittest.mock import patch

from src.agents.orchestrator_agent import plan_orchestration, _fallback_orchestration


def test_fallback_orchestration_frontend_project():
    """测试 fallback 编排：前端项目创建"""
    task_text = "创建一个 React 前端项目"
    repo_summary = {}

    result = _fallback_orchestration(task_text, repo_summary)

    assert result["mode"] == "fallback"
    assert result["passed"] is True
    assert result["task_type"] == "create_frontend_project"
    assert result["complexity"] == "high"
    assert result["should_require_tests"] is True
    assert result["recommended_mode"] == "standard"


def test_fallback_orchestration_bugfix():
    """测试 fallback 编排：bug 修复"""
    task_text = "修复登录页面的 bug"
    repo_summary = {}

    result = _fallback_orchestration(task_text, repo_summary)

    assert result["mode"] == "fallback"
    assert result["passed"] is True
    assert result["task_type"] == "bugfix"
    assert result["complexity"] == "medium"
    assert result["should_require_tests"] is True


def test_fallback_orchestration_documentation():
    """测试 fallback 编排：文档任务"""
    task_text = "更新 README 文档"
    repo_summary = {}

    result = _fallback_orchestration(task_text, repo_summary)

    assert result["mode"] == "fallback"
    assert result["passed"] is True
    assert result["task_type"] == "documentation"
    assert result["complexity"] == "low"
    assert result["should_require_tests"] is False


def test_plan_orchestration_llm_disabled():
    """测试 LLM 禁用时使用 fallback"""
    task_text = "创建一个新功能"
    project_config = {
        "crewai": {
            "orchestration_mode": "hybrid",
            "llm": {
                "model": "test-model",
                "api_key": "test-key",
            }
        }
    }

    with patch.dict(os.environ, {"CREWAI_DISABLE_LLM": "1"}):
        result = plan_orchestration(task_text, project_config)

    assert result["mode"] == "fallback"
    assert result["passed"] is True


def test_plan_orchestration_hybrid_mode_fallback():
    """测试 hybrid 模式下 LLM 失败时 fallback"""
    task_text = "创建一个新功能"
    project_config = {
        "crewai": {
            "orchestration_mode": "hybrid",
            "llm": {
                "model": "",  # 无效配置
                "api_key": "",
            }
        }
    }

    with patch.dict(os.environ, {}, clear=True):
        result = plan_orchestration(task_text, project_config)

    # hybrid 模式下应该 fallback
    assert result["mode"] == "fallback"
    assert result["passed"] is True


def test_plan_orchestration_intelligent_mode_failure():
    """测试 intelligent 模式下 LLM 失败时抛出异常"""
    task_text = "创建一个新功能"
    project_config = {
        "crewai": {
            "orchestration_mode": "intelligent",
            "llm": {
                "model": "",  # 无效配置
                "api_key": "",
            }
        }
    }

    with patch.dict(os.environ, {}, clear=True):
        try:
            plan_orchestration(task_text, project_config)
            assert False, "Should have raised RuntimeError"
        except RuntimeError as e:
            assert "intelligent mode" in str(e).lower()


def test_fallback_orchestration_structure():
    """测试 fallback 编排返回的数据结构"""
    task_text = "实现用户认证功能"
    repo_summary = {}

    result = _fallback_orchestration(task_text, repo_summary)

    # 验证必需字段
    assert "mode" in result
    assert "passed" in result
    assert "task_type" in result
    assert "complexity" in result
    assert "recommended_mode" in result
    assert "should_explore" in result
    assert "should_use_opencode_plan" in result
    assert "should_require_tests" in result
    assert "risk_level" in result
    assert "reasoning_summary" in result
    assert "task_contract_hints" in result
    assert "execution_strategy" in result
    assert "failure_policy" in result

    # 验证嵌套结构
    assert isinstance(result["task_contract_hints"], dict)
    assert isinstance(result["execution_strategy"], list)
    assert isinstance(result["failure_policy"], dict)
    assert "max_iterations" in result["failure_policy"]


def test_fallback_orchestration_test_task():
    """测试 fallback 编排：测试任务"""
    task_text = "为登录功能添加单元测试"
    repo_summary = {}

    result = _fallback_orchestration(task_text, repo_summary)

    assert result["task_type"] == "test_generation"
    assert result["complexity"] == "low"
    assert result["should_require_tests"] is True


def test_fallback_orchestration_refactor_task():
    """测试 fallback 编排：重构任务"""
    task_text = "重构用户服务代码"
    repo_summary = {}

    result = _fallback_orchestration(task_text, repo_summary)

    assert result["task_type"] == "refactor"
    assert result["complexity"] == "medium"
    assert result["should_require_tests"] is True

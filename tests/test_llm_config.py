"""
测试 LLM 配置检查功能
"""
import os
from unittest.mock import patch

from src.agents.llm_factory import check_llm_config, require_llm, get_llm_settings


def test_check_llm_config_not_configured():
    """测试 LLM 未配置的情况"""
    config = {
        "crewai": {
            "llm": {
                "model": "",
                "api_key": "",
            }
        }
    }

    with patch.dict(os.environ, {}, clear=True):
        result = check_llm_config(config)

    assert result["configured"] is False
    assert "LLM_MODEL" in str(result["errors"])
    assert "api_key" in str(result["errors"])


def test_check_llm_config_configured():
    """测试 LLM 已配置的情况"""
    config = {
        "crewai": {
            "llm": {
                "model": "claude-sonnet-4-6",
                "base_url": "https://api.example.com",
                "api_key": "test-key",
                "temperature": 0.1,
            }
        }
    }

    with patch.dict(os.environ, {}, clear=True):
        result = check_llm_config(config)

    assert result["configured"] is True
    assert result["crewai_installed"] is True
    assert result["model"] == "claude-sonnet-4-6"
    assert result["base_url"] == "https://api.example.com"
    assert result["api_key_present"] is True
    assert result["temperature"] == 0.1
    assert len(result["errors"]) == 0


def test_check_llm_config_env_override():
    """测试环境变量覆盖配置"""
    config = {
        "crewai": {
            "llm": {
                "model": "config-model",
                "api_key": "config-key",
            }
        }
    }

    with patch.dict(os.environ, {
        "LLM_MODEL": "env-model",
        "LLM_API_KEY": "env-key",
        "LLM_BASE_URL": "https://env.example.com",
    }):
        result = check_llm_config(config)

    assert result["configured"] is True
    assert result["model"] == "env-model"
    assert result["base_url"] == "https://env.example.com"
    assert result["api_key_present"] is True


def test_require_llm_success():
    """测试 require_llm 成功的情况"""
    config = {
        "crewai": {
            "llm": {
                "model": "claude-sonnet-4-6",
                "api_key": "test-key",
            }
        }
    }

    with patch.dict(os.environ, {}, clear=True):
        # 不应该抛出异常
        require_llm(config)


def test_require_llm_failure():
    """测试 require_llm 失败的情况"""
    config = {
        "crewai": {
            "llm": {
                "model": "",
                "api_key": "",
            }
        }
    }

    with patch.dict(os.environ, {}, clear=True):
        try:
            require_llm(config)
            assert False, "Should have raised RuntimeError"
        except RuntimeError as e:
            assert "not properly configured" in str(e)
            assert "LLM_MODEL" in str(e)


def test_get_llm_settings_priority():
    """测试 LLM 设置的优先级：环境变量 > 配置文件"""
    config = {
        "crewai": {
            "llm": {
                "model": "config-model",
                "base_url": "https://config.example.com",
                "api_key": "config-key",
                "temperature": "0.5",
            }
        }
    }

    # 环境变量应该覆盖配置文件
    with patch.dict(os.environ, {
        "LLM_MODEL": "env-model",
        "LLM_TEMPERATURE": "0.2",
    }):
        settings = get_llm_settings(config)

    assert settings["model"] == "env-model"
    assert settings["base_url"] == "https://config.example.com"  # 未被环境变量覆盖
    assert settings["api_key"] == "config-key"  # 未被环境变量覆盖
    assert settings["temperature"] == 0.2  # 环境变量覆盖


def test_get_llm_settings_claude_fallback():
    """测试 CLAUDE_* 环境变量作为备选"""
    config = {
        "crewai": {
            "llm": {}
        }
    }

    with patch.dict(os.environ, {
        "CLAUDE_MODEL": "claude-model",
        "CLAUDE_API_KEY": "claude-key",
        "CLAUDE_BASE_URL": "https://claude.example.com",
    }):
        settings = get_llm_settings(config)

    assert settings["model"] == "claude-model"
    assert settings["api_key"] == "claude-key"
    assert settings["base_url"] == "https://claude.example.com"


def test_check_llm_config_no_base_url_warning():
    """测试没有 base_url 时的警告"""
    config = {
        "crewai": {
            "llm": {
                "model": "claude-sonnet-4-6",
                "api_key": "test-key",
                "base_url": "",
            }
        }
    }

    with patch.dict(os.environ, {}, clear=True):
        result = check_llm_config(config)

    assert result["configured"] is True
    assert len(result["warnings"]) > 0
    assert "base_url" in str(result["warnings"]).lower()

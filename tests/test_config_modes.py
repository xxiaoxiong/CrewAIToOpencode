from src.config_loader import get_effective_pipeline, get_project_config


def test_opencode_agents_mapping_read_from_config():
    config = get_project_config("demo-project")

    assert config["opencode_agents"]["explorer"] == "explore"
    assert config["opencode_agents"]["planner"] == "plan"
    assert config["opencode_agents"]["coder"] == "build"
    assert config["opencode_agents"]["repairer"] == "build"


def test_quick_standard_full_mode_pipeline_merge():
    config = get_project_config("demo-project")

    quick = get_effective_pipeline(config, "quick")
    standard = get_effective_pipeline(config, "standard")
    full = get_effective_pipeline(config, "full")

    assert quick["explore_enabled"] is False
    assert quick["architect_enabled"] is False
    assert quick["opencode_plan_enabled"] is False
    assert standard["explore_enabled"] is True
    assert standard["opencode_plan_enabled"] is False
    assert full["explore_enabled"] is True
    assert full["architect_enabled"] is True
    assert full["opencode_plan_enabled"] is True
    assert full["max_iterations"] == 3

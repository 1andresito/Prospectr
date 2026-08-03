import pytest

import env_manager


@pytest.fixture
def env_path(tmp_path):
    return tmp_path / ".env"


def test_save_then_clear_removes_the_key(env_path):
    env_manager.save_keys(env_path, {"GOOGLE_PLACES_API_KEY": "abc123"})
    assert env_manager.get_key_status(env_path)[0]["is_set"] is True

    removed = env_manager.clear_keys(env_path, ["GOOGLE_PLACES_API_KEY"])

    assert removed == ["GOOGLE_PLACES_API_KEY"]
    assert env_manager.get_key_status(env_path)[0]["is_set"] is False


def test_clear_leaves_other_settings_intact(env_path):
    env_manager.save_keys(
        env_path,
        {"GOOGLE_PLACES_API_KEY": "places", "AGENT_API_KEY": "agent"},
    )
    env_manager.save_active_provider(env_path, "claude")
    env_manager.save_grid_size(env_path, 4)

    env_manager.clear_keys(env_path, ["AGENT_API_KEY"])

    status = {item["name"]: item for item in env_manager.get_key_status(env_path)}
    assert status["GOOGLE_PLACES_API_KEY"]["is_set"] is True
    assert status["AGENT_API_KEY"]["is_set"] is False
    assert env_manager.get_active_provider(env_path) == "claude"
    assert env_manager.get_grid_size(env_path) == 4


def test_clearing_an_absent_key_is_a_no_op(env_path):
    assert env_manager.clear_keys(env_path, ["AGENT_API_KEY"]) == []


def test_preview_never_exposes_the_whole_key(env_path):
    env_manager.save_keys(env_path, {"GOOGLE_PLACES_API_KEY": "supersecret9999"})
    preview = env_manager.get_key_status(env_path)[0]["preview"]

    assert preview == "••••9999"
    assert "supersecret" not in preview


def test_grid_size_is_clamped_to_the_supported_range(env_path):
    with pytest.raises(ValueError):
        env_manager.save_grid_size(env_path, 99)

    with pytest.raises(ValueError):
        env_manager.save_grid_size(env_path, "not a number")

    env_path.write_text("SEARCH_GRID_SIZE=99\n", encoding="utf-8")
    assert env_manager.get_grid_size(env_path) == env_manager.MAX_GRID_SIZE


def test_unknown_provider_falls_back_to_the_default(env_path):
    env_path.write_text("AI_PROVIDER=notreal\n", encoding="utf-8")
    assert env_manager.get_active_provider(env_path) == env_manager.DEFAULT_PROVIDER


@pytest.mark.parametrize(
    "provider, key, is_valid",
    [
        ("claude", "sk-ant-abc", True),
        ("chatgpt", "sk-abc", True),
        ("nvidia", "nvapi-abc", True),
        ("gemini", "AIzaabc", True),
        # An Anthropic key must not be mistaken for an OpenAI one just because
        # both begin with "sk-".
        ("chatgpt", "sk-ant-abc", False),
        ("nvidia", "sk-ant-abc", False),
        ("claude", "sk-abc", False),
        # Unrecognised formats are allowed through so new key styles do not
        # require a client update.
        ("claude", "brand-new-format", True),
        ("claude", "", True),
    ],
)
def test_validate_provider_key(provider, key, is_valid):
    valid, error = env_manager.validate_provider_key(provider, key)

    assert valid is is_valid
    assert (error is None) is is_valid

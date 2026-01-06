import yaml
import pytest
from wyoming_tts_proxy.__main__ import load_config
from wyoming_tts_proxy.config import ProxyConfig


def test_load_empty_config():
    assert load_config(None) == ProxyConfig()
    assert load_config("") == ProxyConfig()


def test_load_valid_config(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_data = {
        "normalize_markdown": True,
        "remove_emoji": False,
        "replacements": [{"regex": "a", "replace": "b"}],
    }
    with open(config_file, "w") as f:
        yaml.dump(config_data, f)

    loaded = load_config(str(config_file))
    assert loaded.normalize_markdown
    assert not loaded.remove_emoji
    assert len(loaded.replacements) == 1
    assert loaded.replacements[0].regex.pattern == "a"
    assert loaded.replacements[0].replace == "b"


def test_load_partial_config_markdown(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_data = {"normalize_markdown": True}
    with open(config_file, "w") as f:
        yaml.dump(config_data, f)

    loaded = load_config(str(config_file))
    assert loaded.normalize_markdown
    assert not loaded.remove_emoji  # default
    assert loaded.remove_asterisks  # default


def test_load_partial_config_emoji(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_data = {"remove_emoji": True}
    with open(config_file, "w") as f:
        yaml.dump(config_data, f)

    loaded = load_config(str(config_file))
    assert not loaded.normalize_markdown  # default
    assert loaded.remove_emoji
    assert loaded.remove_asterisks  # default


def test_load_partial_config_replacements(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_data = {"replacements": [{"regex": "foo", "replace": "bar"}]}
    with open(config_file, "w") as f:
        yaml.dump(config_data, f)

    loaded = load_config(str(config_file))
    assert len(loaded.replacements) == 1
    assert loaded.replacements[0].regex.pattern == "foo"
    assert not loaded.normalize_markdown  # default


def test_load_invalid_config_format(tmp_path):
    config_file = tmp_path / "config.yaml"
    with open(config_file, "w") as f:
        f.write("not a dictionary")

    with pytest.raises(SystemExit):
        load_config(str(config_file))


def test_load_invalid_replacements_format(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_data = {"replacements": "not a list"}
    with open(config_file, "w") as f:
        yaml.dump(config_data, f)

    with pytest.raises(SystemExit):
        load_config(str(config_file))


def test_load_invalid_regex_pattern(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_data = {
        "replacements": [
            {"regex": "[", "replace": "error"}  # Invalid regex
        ]
    }
    with open(config_file, "w") as f:
        yaml.dump(config_data, f)

    with pytest.raises(SystemExit):
        load_config(str(config_file))


def test_load_missing_config_file():
    with pytest.raises(SystemExit):
        load_config("non_existent_file.yaml")


def test_load_malformed_yaml(tmp_path):
    config_file = tmp_path / "config.yaml"
    with open(config_file, "w") as f:
        f.write("normalize_markdown: [")  # Invalid YAML

    with pytest.raises(SystemExit):
        load_config(str(config_file))


def test_load_missing_required_regex(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_data = {
        "replacements": [
            {"replace": "something"}  # missing 'regex'
        ]
    }
    with open(config_file, "w") as f:
        yaml.dump(config_data, f)

    with pytest.raises(SystemExit):
        load_config(str(config_file))


def test_load_incorrect_type_in_config(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_data = {"normalize_markdown": "not-a-boolean-that-can-be-coerced-easily"}
    # Note: Pydantic might coerce "true", "false", "1", "0" but not random strings
    with open(config_file, "w") as f:
        yaml.dump(config_data, f)

    with pytest.raises(SystemExit):
        load_config(str(config_file))

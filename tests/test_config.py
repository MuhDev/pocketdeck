import pytest
from pydantic import ValidationError
from server.config import ServerConfig, DiscordConfig, PresetConfig, AppConfig, settings

def test_server_config():
    cfg = ServerConfig(host="127.0.0.1", port=9000, pin_hash="testhash")
    assert cfg.host == "127.0.0.1"
    assert cfg.port == 9000
    assert cfg.pin_hash == "testhash"

def test_preset_config_valid():
    preset = PresetConfig(
        id="test-app",
        name="Test App",
        type="app",
        target="C:\\Windows\\notepad.exe",
        args=["--test"],
        accent="#ff0000"
    )
    assert preset.id == "test-app"
    assert preset.type == "app"
    assert preset.args == ["--test"]

def test_preset_config_invalid_type():
    with pytest.raises(ValidationError):
        PresetConfig(
            id="bad-app",
            name="Bad App",
            type="invalid_type",  # type: ignore
            target="target"
        )

def test_loaded_settings():
    assert settings.server is not None
    assert isinstance(settings.server.port, int)
    assert isinstance(settings.presets, list)
    assert isinstance(settings.discord.mute_hotkey, list)

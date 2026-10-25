import pytest
from server.services.config_store import _slugify, serialize_preset
from server.config import PresetConfig

def test_slugify():
    existing = {"steam", "steam-2"}
    assert _slugify("Steam", existing) == "steam-3"
    assert _slugify("My Cool App!", set()) == "my-cool-app"
    assert _slugify("", set()) == "app"

def test_serialize_preset():
    preset = PresetConfig(
        id="unit-test-preset",
        name="Unit Test Preset",
        type="url",
        target="https://github.com",
        args=None,
        icon=None,
        accent=None
    )
    serialized = serialize_preset(preset)
    assert serialized["id"] == "unit-test-preset"
    assert serialized["name"] == "Unit Test Preset"
    assert serialized["type"] == "url"
    assert serialized["target"] == "https://github.com"
    assert "icon_url" in serialized
    assert serialized["icon_url"].startswith("/api/icons/preset/unit-test-preset")

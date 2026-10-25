import yaml
import os
from typing import Literal
from pydantic import BaseModel, Field

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")

class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8765
    pin_hash: str

class DiscordConfig(BaseModel):
    mute_hotkey: list[str]
    deafen_hotkey: list[str]

DEFAULT_PIN_HASH = "03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4"

class PresetConfig(BaseModel):
    id: str
    name: str
    type: Literal["app", "url", "folder", "steam", "shell_app"]
    target: str
    args: list[str] | None = None
    icon: str | None = None
    accent: str | None = None

class AppConfig(BaseModel):
    server: ServerConfig
    discord: DiscordConfig
    presets: list[PresetConfig] = Field(default_factory=list)

import shutil

def load_config() -> AppConfig:
    if not os.path.exists(CONFIG_PATH):
        example_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.example.yaml")
        if os.path.exists(example_path):
            shutil.copyfile(example_path, CONFIG_PATH)
            print(f"[PocketDeck] Initialized config.yaml from config.example.yaml")
        else:
            raise FileNotFoundError(f"Configuration file not found: {CONFIG_PATH}")
    
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        
    return AppConfig(**data)

# Global config instance
settings = load_config()

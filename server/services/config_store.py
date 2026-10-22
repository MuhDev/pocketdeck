import os
import re
import hashlib
import threading
from typing import List, Optional, Dict, Any
from ruamel.yaml import YAML

from server.config import CONFIG_PATH, PresetConfig, settings
from server.services import icon_svc

_store_lock = threading.Lock()
_yaml = YAML()
_yaml.preserve_quotes = True
_yaml.indent(mapping=2, sequence=4, offset=2)


def _slugify(name: str, existing_ids: set) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", (name or "app").lower()).strip("-")
    if not base:
        base = "app"
    candidate = base
    counter = 2
    while candidate in existing_ids:
        candidate = f"{base}-{counter}"
        counter += 1
    return candidate


def serialize_preset(preset: PresetConfig) -> Dict[str, Any]:
    _, accent = icon_svc.get_preset_icon(preset)
    ver_src = f"{preset.type}:{preset.target}:{preset.icon or ''}"
    ver = hashlib.sha1(ver_src.encode("utf-8")).hexdigest()[:8]
    return {
        "id": preset.id,
        "name": preset.name,
        "type": preset.type,
        "target": preset.target,
        "args": preset.args,
        "icon": preset.icon,
        "accent": preset.accent or accent,
        "icon_url": f"/api/icons/preset/{preset.id}?v={ver}",
    }


def _persist_presets_locked(presets: List[PresetConfig]):
    """Writes updated presets list to config.yaml while preserving comments and formatting."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        doc = _yaml.load(f)

    serialized_list = []
    for p in presets:
        item: Dict[str, Any] = {
            "id": p.id,
            "name": p.name,
            "type": p.type,
            "target": p.target,
        }
        if p.args:
            item["args"] = list(p.args)
        if p.icon:
            item["icon"] = p.icon
        if p.accent:
            item["accent"] = p.accent
        serialized_list.append(item)

    doc["presets"] = serialized_list

    tmp_path = CONFIG_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        _yaml.dump(doc, f)
    os.replace(tmp_path, CONFIG_PATH)
    settings.presets = list(presets)


def add_preset(
    name: str,
    preset_type: str,
    target: str,
    args: Optional[List[str]] = None,
    icon: Optional[str] = None,
    preset_id: Optional[str] = None,
    index: Optional[int] = None,
) -> PresetConfig:
    clean_name = (name or "").strip()[:60]
    clean_target = (target or "").strip()
    if not clean_name or not clean_target:
        raise ValueError("Name and target are required")
    if preset_type not in ("app", "url", "folder", "steam", "shell_app"):
        raise ValueError(f"Unsupported preset type: {preset_type}")
    if preset_type == "url" and not re.match(r"^https?://", clean_target, re.I):
        clean_target = "https://" + clean_target

    with _store_lock:
        current = list(settings.presets)
        existing_ids = {p.id for p in current}
        if preset_id and preset_id not in existing_ids:
            new_id = preset_id
        else:
            new_id = _slugify(clean_name, existing_ids)

        new_preset = PresetConfig(
            id=new_id,
            name=clean_name,
            type=preset_type,
            target=clean_target,
            args=args if args else None,
            icon=icon,
        )
        if index is not None and 0 <= index <= len(current):
            current.insert(index, new_preset)
        else:
            current.append(new_preset)

        _persist_presets_locked(current)
        return new_preset


def update_preset(
    preset_id: str,
    name: Optional[str] = None,
    target: Optional[str] = None,
    args: Optional[List[str]] = None,
    icon: Optional[str] = None,
) -> Optional[PresetConfig]:
    with _store_lock:
        current = list(settings.presets)
        target_preset = None
        for p in current:
            if p.id == preset_id:
                target_preset = p
                break
        if not target_preset:
            return None

        if name is not None:
            clean_name = name.strip()[:60]
            if clean_name:
                target_preset.name = clean_name
        if target is not None:
            clean_target = target.strip()
            if clean_target:
                if target_preset.type == "url" and not re.match(r"^https?://", clean_target, re.I):
                    clean_target = "https://" + clean_target
                target_preset.target = clean_target
        if args is not None:
            target_preset.args = args if args else None
        if icon is not None:
            target_preset.icon = icon if icon else None

        _persist_presets_locked(current)
        return target_preset


def delete_preset(preset_id: str) -> bool:
    with _store_lock:
        current = list(settings.presets)
        filtered = [p for p in current if p.id != preset_id]
        if len(filtered) == len(current):
            return False
        _persist_presets_locked(filtered)
        return True


def reorder_presets(ordered_ids: List[str]) -> List[PresetConfig]:
    with _store_lock:
        current = list(settings.presets)
        by_id = {p.id: p for p in current}
        new_order: List[PresetConfig] = []
        seen = set()
        for pid in ordered_ids:
            if pid in by_id and pid not in seen:
                new_order.append(by_id[pid])
                seen.add(pid)
        for p in current:
            if p.id not in seen:
                new_order.append(p)
        _persist_presets_locked(new_order)
        return new_order

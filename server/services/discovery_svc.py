import json
import time
import hashlib
import subprocess
import threading
from typing import List, Dict, Optional

_cache_lock = threading.Lock()
_installed_apps: List[Dict[str, str]] = []
_key_to_app: Dict[str, Dict[str, str]] = {}
_last_fetched: float = 0.0
CACHE_TTL_SECONDS = 300.0

_NOISE_KEYWORDS = (
    "uninstall",
    "uninst",
    "remove ",
    "readme",
    "release notes",
    "documentation",
    "manual",
    "help",
    "website",
    "license",
    "updater",
)
_NOISE_EXTENSIONS = (".chm", ".hlp", ".txt", ".pdf", ".html", ".htm", ".url")


def _fetch_start_apps() -> List[Dict[str, str]]:
    cmd = [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; Get-StartApps | Select-Object Name, AppID | ConvertTo-Json -Compress",
    ]
    try:
        # CREATE_NO_WINDOW = 0x08000000
        out = subprocess.check_output(
            cmd, text=True, encoding="utf-8", errors="replace", creationflags=0x08000000, timeout=10
        ).strip()
        if not out:
            return []
        raw = json.loads(out)
        if isinstance(raw, dict):
            raw = [raw]
    except Exception as e:
        print(f"Error discovering installed apps: {e}")
        return []

    seen_names = set()
    results: List[Dict[str, str]] = []

    for item in raw:
        name = (item.get("Name") or "").strip()
        app_id = (item.get("AppID") or "").strip()
        if not name or not app_id:
            continue

        name_lower = name.lower()
        app_id_lower = app_id.lower()

        if any(k in name_lower for k in _NOISE_KEYWORDS):
            continue
        if any(app_id_lower.endswith(ext) for ext in _NOISE_EXTENSIONS):
            continue
        if name_lower in seen_names:
            continue

        seen_names.add(name_lower)
        key = hashlib.sha1(app_id.encode("utf-8")).hexdigest()[:12]
        results.append(
            {
                "key": key,
                "name": name,
                "app_id": app_id,
                "icon_url": f"/api/icons/installed/{key}",
            }
        )

    results.sort(key=lambda x: x["name"].lower())
    return results


def get_installed_apps(query: str = "", force_refresh: bool = False) -> List[Dict[str, str]]:
    global _installed_apps, _key_to_app, _last_fetched
    now = time.time()
    with _cache_lock:
        if force_refresh or not _installed_apps or (now - _last_fetched > CACHE_TTL_SECONDS):
            apps = _fetch_start_apps()
            if apps:
                _installed_apps = apps
                _key_to_app = {a["key"]: a for a in apps}
                _last_fetched = now

        apps_snapshot = list(_installed_apps)

    q = (query or "").strip().lower()
    if not q:
        return apps_snapshot
    return [a for a in apps_snapshot if q in a["name"].lower() or q in a["app_id"].lower()]


def resolve_installed_key(key: str) -> Optional[Dict[str, str]]:
    with _cache_lock:
        found = _key_to_app.get(key)
    if found:
        return found
    # Populate cache if empty
    get_installed_apps()
    with _cache_lock:
        return _key_to_app.get(key)

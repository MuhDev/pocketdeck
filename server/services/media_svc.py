import os
import time
import json
import shutil
import hashlib
import urllib.parse
import urllib.request
import subprocess
from typing import Dict, Any, Optional, Set

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "media")
THUMB_CACHE_DIR = os.path.join(CACHE_DIR, "cache")
CURRENT_THUMB_PATH = os.path.join(CACHE_DIR, "now_playing.jpg")
SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "get_media.ps1")

os.makedirs(THUMB_CACHE_DIR, exist_ok=True)

_last_poll_time = 0.0
_poll_cache_ttl = 1.2  # Cache for 1.2 seconds to avoid slamming PowerShell
_cached_state: Dict[str, Any] = {
    "has_media": False,
    "title": "",
    "artist": "",
    "album": "",
    "status": "Stopped",
    "app": "",
    "app_id": "",
    "position_ms": 0,
    "duration_ms": 0,
    "has_thumbnail": False,
    "thumb_url": None,
}
_current_thumb_file: Optional[str] = None
_negative_cache: Set[str] = set()


def _get_track_hash(artist: str, title: str) -> str:
    norm_artist = (artist or "").strip().lower()
    norm_title = (title or "").strip().lower()
    return hashlib.md5(f"{norm_artist}:{norm_title}".encode("utf-8")).hexdigest()[:12]


def _download_and_cache(url: str, dest_path: str) -> bool:
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        )
        with urllib.request.urlopen(req, timeout=3.5) as resp:
            content = resp.read()
            if content and len(content) > 1000:
                with open(dest_path, "wb") as f:
                    f.write(content)
                return True
    except Exception:
        pass
    return False


def _fetch_online_artwork(artist: str, title: str, album: str = "") -> Optional[str]:
    """Fetch official high-res album artwork via iTunes Search API with Deezer fallback."""
    if not title and not artist:
        return None

    track_hash = _get_track_hash(artist, title)
    dest_path = os.path.join(THUMB_CACHE_DIR, f"{track_hash}.jpg")

    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 1000:
        return dest_path

    if track_hash in _negative_cache:
        return None

    # Search candidates in priority order
    queries = []
    clean_artist = artist.replace("&", " ").replace("feat.", " ").strip() if artist else ""
    clean_title = title.replace("&", " ").replace("feat.", " ").strip() if title else ""

    if clean_artist and clean_title:
        queries.append(f"{clean_artist} {clean_title}")
    if clean_title:
        queries.append(clean_title)
    if clean_artist and album:
        queries.append(f"{clean_artist} {album}")

    # 1. Try iTunes Search API
    for q in queries:
        try:
            encoded_q = urllib.parse.quote_plus(q)
            itunes_url = f"https://itunes.apple.com/search?term={encoded_q}&entity=song&limit=1"
            req = urllib.request.Request(
                itunes_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            )
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("resultCount", 0) > 0:
                    artwork_url = data["results"][0].get("artworkUrl100", "")
                    if artwork_url:
                        # Upgrade to 600x600 high resolution
                        highres = artwork_url.replace("100x100bb", "600x600bb")
                        if _download_and_cache(highres, dest_path):
                            return dest_path
        except Exception:
            pass

    # 2. Try Deezer Search API
    for q in queries:
        try:
            encoded_q = urllib.parse.quote_plus(q)
            deezer_url = f"https://api.deezer.com/search?q={encoded_q}&limit=1"
            req = urllib.request.Request(
                deezer_url,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                results = data.get("data", [])
                if results and len(results) > 0:
                    album_data = results[0].get("album", {})
                    artwork_url = album_data.get("cover_big") or album_data.get("cover_medium")
                    if artwork_url and _download_and_cache(artwork_url, dest_path):
                        return dest_path
        except Exception:
            pass

    _negative_cache.add(track_hash)
    return None


def poll_media() -> Dict[str, Any]:
    global _last_poll_time, _cached_state, _current_thumb_file

    now = time.time()
    if now - _last_poll_time < _poll_cache_ttl and _cached_state:
        return _cached_state

    _last_poll_time = now

    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        SCRIPT_PATH,
        "-ThumbPath",
        CURRENT_THUMB_PATH,
    ]

    try:
        res = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=3.5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

        out = res.stdout.strip()
        if out:
            data = json.loads(out)
            has_media = bool(data.get("has_media"))
            title = data.get("title", "").strip()
            artist = data.get("artist", "").strip()
            album = data.get("album", "").strip()
            status = data.get("status", "Stopped")
            app_name = data.get("app", "Media")
            pos_ms = int(data.get("position_ms", 0))
            dur_ms = int(data.get("duration_ms", 0))
            ps_has_thumb = bool(data.get("has_thumbnail"))

            thumb_file = None
            thumb_url = None

            if has_media and (title or artist):
                track_hash = _get_track_hash(artist, title)
                cached_thumb = os.path.join(THUMB_CACHE_DIR, f"{track_hash}.jpg")

                # If GSMTC provided a fresh thumbnail stream, save it to the track cache
                if ps_has_thumb and os.path.exists(CURRENT_THUMB_PATH) and os.path.getsize(CURRENT_THUMB_PATH) > 1000:
                    try:
                        shutil.copy2(CURRENT_THUMB_PATH, cached_thumb)
                        thumb_file = cached_thumb
                    except Exception:
                        thumb_file = CURRENT_THUMB_PATH
                elif os.path.exists(cached_thumb) and os.path.getsize(cached_thumb) > 1000:
                    thumb_file = cached_thumb
                else:
                    # Online artwork fetch (iTunes / Deezer)
                    thumb_file = _fetch_online_artwork(artist, title, album)

                if thumb_file and os.path.exists(thumb_file):
                    thumb_url = f"/api/media/thumbnail?v={track_hash}"

            _current_thumb_file = thumb_file
            has_thumb = bool(thumb_file and os.path.exists(thumb_file))

            _cached_state = {
                "has_media": has_media,
                "title": title,
                "artist": artist,
                "album": album,
                "status": status,
                "app": app_name,
                "position_ms": pos_ms,
                "duration_ms": dur_ms,
                "has_thumbnail": has_thumb,
                "thumb_url": thumb_url,
            }
            return _cached_state
    except Exception:
        pass

    return _cached_state


def get_now_playing() -> Dict[str, Any]:
    return poll_media()


def get_thumbnail_path(v: Optional[str] = None) -> Optional[str]:
    poll_media()
    if v:
        # Sanitize v to prevent path traversal
        clean_v = "".join(c for c in v if c.isalnum() or c in "-_")
        specific = os.path.join(THUMB_CACHE_DIR, f"{clean_v}.jpg")
        if os.path.exists(specific) and os.path.getsize(specific) > 1000:
            return specific

    if _current_thumb_file and os.path.exists(_current_thumb_file):
        return _current_thumb_file
    if os.path.exists(CURRENT_THUMB_PATH) and os.path.getsize(CURRENT_THUMB_PATH) > 1000:
        return CURRENT_THUMB_PATH
    return None

import os
import platform
from fastapi import APIRouter, Depends, HTTPException, Body, UploadFile, File, Query
from fastapi.responses import FileResponse
from typing import Dict, Any, List, Optional

from server.auth import get_token_header, verify_pin
from server.config import settings, DEFAULT_PIN_HASH
from server.services import (
    keyboard_svc,
    audio_svc,
    clipboard_svc,
    launcher_svc,
    power_svc,
    stats_svc,
    icon_svc,
    discovery_svc,
    config_store,
    media_svc,
    obs_svc,
)

router = APIRouter()
protected_router = APIRouter(dependencies=[Depends(get_token_header)])

# --- Auth ---

@router.post("/auth/login")
def login(pin: str = Body(..., embed=True)):
    token = verify_pin(pin)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid PIN")
    return {
        "token": token,
        "default_pin": settings.server.pin_hash == DEFAULT_PIN_HASH,
        "hostname": platform.node() or "My PC",
    }


@router.post("/server/shutdown")
def shutdown_server():
    import threading
    import time
    import signal
    def _exit():
        time.sleep(0.1)
        try:
            ppid = os.getppid()
            if ppid > 0:
                os.kill(ppid, signal.SIGTERM)
        except Exception:
            pass
        os._exit(0)
    threading.Thread(target=_exit, daemon=True).start()
    return {"status": "shutting down"}


# --- Icons (served directly for <img> tags with HTTP caching) ---

@router.get("/icons/preset/{preset_id}")
def get_preset_icon_endpoint(preset_id: str):
    preset = next((p for p in settings.presets if p.id == preset_id), None)
    if not preset:
        png_path = os.path.join(icon_svc.CACHE_DIR, f"fallback_{preset_id}.png")
        if not os.path.exists(png_path):
            im = icon_svc.generate_fallback_icon(preset_id, 256)
            im.save(png_path, "PNG")
        return FileResponse(png_path, media_type="image/png")

    png_path, _ = icon_svc.get_preset_icon(preset)
    return FileResponse(
        png_path,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.get("/icons/process/{proc_name}")
def get_process_icon_endpoint(proc_name: str):
    png_path, _ = icon_svc.get_process_icon(proc_name)
    return FileResponse(
        png_path,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.get("/icons/installed/{app_key}")
def get_installed_icon_endpoint(app_key: str):
    info = discovery_svc.resolve_installed_key(app_key)
    if not info:
        png_path = os.path.join(icon_svc.CACHE_DIR, "fallback_installed.png")
        if not os.path.exists(png_path):
            im = icon_svc.generate_fallback_icon("App", 256)
            im.save(png_path, "PNG")
        return FileResponse(png_path, media_type="image/png")

    png_path, _ = icon_svc.get_installed_app_icon(info["app_id"], info["name"])
    return FileResponse(
        png_path,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.get("/media/thumbnail")
def get_media_thumbnail(v: Optional[str] = Query(None)):
    path = media_svc.get_thumbnail_path(v)
    if path and os.path.exists(path):
        return FileResponse(
            path,
            media_type="image/jpeg",
            headers={
                "Cache-Control": "public, max-age=86400",
                "Access-Control-Allow-Origin": "*",
            },
        )
    raise HTTPException(status_code=404, detail="No media thumbnail found")


# --- Discord ---

@protected_router.post("/discord/mute")
def toggle_discord_mute():
    keyboard_svc.press_hotkey(settings.discord.mute_hotkey)
    return {"status": "ok"}


@protected_router.post("/discord/deafen")
def toggle_discord_deafen():
    keyboard_svc.press_hotkey(settings.discord.deafen_hotkey)
    return {"status": "ok"}


# --- Keyboard (Note: /keys/type MUST precede /keys/{action}) ---

@protected_router.post("/keys/type")
def type_text(text: str = Body(..., embed=True)):
    keyboard_svc.type_text(text)
    return {"status": "ok"}


@protected_router.post("/keys/{action}")
def send_keys(action: str):
    valid_actions = {
        "copy": keyboard_svc.send_copy,
        "paste": keyboard_svc.send_paste,
        "cut": keyboard_svc.send_cut,
        "undo": keyboard_svc.send_undo,
        "select_all": keyboard_svc.send_select_all,
    }
    if action not in valid_actions:
        raise HTTPException(status_code=404, detail="Action not found")
    valid_actions[action]()
    return {"status": "ok"}


# --- Mouse ---

@protected_router.post("/mouse/move")
def mouse_move(dx: int = Body(..., embed=True), dy: int = Body(..., embed=True)):
    keyboard_svc.move_mouse(dx, dy)
    return {"status": "ok"}


@protected_router.post("/mouse/click")
def mouse_click(btn: str = Body("left", embed=True), double: bool = Body(False, embed=True)):
    keyboard_svc.click_mouse(btn, double)
    return {"status": "ok"}


@protected_router.post("/mouse/scroll")
def mouse_scroll(dy: int = Body(..., embed=True)):
    keyboard_svc.scroll_mouse(dy)
    return {"status": "ok"}


# --- Clipboard ---

@protected_router.get("/clipboard")
def get_clipboard():
    return {"text": clipboard_svc.read_clipboard()}


@protected_router.post("/clipboard")
def set_clipboard(text: str = Body(..., embed=True), paste: bool = Body(False, embed=True)):
    clipboard_svc.write_clipboard(text)
    if paste:
        keyboard_svc.send_paste()
    return {"status": "ok"}


# --- Apps & Preset Editor ---

@protected_router.get("/apps")
def list_apps():
    return {
        "presets": [config_store.serialize_preset(p) for p in settings.presets],
        "default_pin": settings.server.pin_hash == DEFAULT_PIN_HASH,
        "hostname": platform.node() or "My PC",
    }


@protected_router.get("/apps/installed")
def list_installed_apps(
    q: str = Query("", description="Search filter"),
    refresh: bool = Query(False, description="Force refresh Start Menu cache"),
):
    return {"apps": discovery_svc.get_installed_apps(q, force_refresh=refresh)}


@protected_router.post("/apps")
def create_app_preset(
    name: str = Body(...),
    type: str = Body(...),
    target: str = Body(...),
    args: Optional[List[str]] = Body(None),
    icon: Optional[str] = Body(None),
    id: Optional[str] = Body(None),
    index: Optional[int] = Body(None),
):
    try:
        preset = config_store.add_preset(
            name=name,
            preset_type=type,
            target=target,
            args=args,
            icon=icon,
            preset_id=id,
            index=index,
        )
        return {"preset": config_store.serialize_preset(preset)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@protected_router.put("/apps/order")
def reorder_app_presets(ids: List[str] = Body(..., embed=True)):
    updated = config_store.reorder_presets(ids)
    return {"presets": [config_store.serialize_preset(p) for p in updated]}


@protected_router.patch("/apps/{preset_id}")
def update_app_preset(
    preset_id: str,
    name: Optional[str] = Body(None),
    target: Optional[str] = Body(None),
    args: Optional[List[str]] = Body(None),
    icon: Optional[str] = Body(None),
):
    preset = config_store.update_preset(
        preset_id=preset_id, name=name, target=target, args=args, icon=icon
    )
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")
    return {"preset": config_store.serialize_preset(preset)}


@protected_router.delete("/apps/{preset_id}")
def delete_app_preset(preset_id: str):
    deleted = config_store.delete_preset(preset_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Preset not found")
    return {"status": "ok"}


@protected_router.post("/apps/{preset_id}/icon")
async def upload_app_preset_icon(preset_id: str, file: UploadFile = File(...)):
    preset = next((p for p in settings.presets if p.id == preset_id), None)
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")
    content = await file.read()
    if not content or len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Invalid or oversized image file")
    try:
        filename = icon_svc.save_custom_icon(preset_id, content)
    except Exception:
        raise HTTPException(status_code=400, detail="Could not process image file")
    updated = config_store.update_preset(preset_id, icon=filename)
    return {"preset": config_store.serialize_preset(updated)}


@protected_router.post("/apps/{preset_id}/launch")
def launch_app(preset_id: str):
    success = launcher_svc.launch_preset(preset_id)
    if not success:
        raise HTTPException(status_code=404, detail="Preset not found or failed to launch")
    return {"status": "ok"}


# --- Audio ---

@protected_router.get("/audio")
def get_audio():
    return audio_svc.get_master_volume()


@protected_router.post("/audio/volume")
def set_audio_volume(level: int = Body(..., embed=True)):
    audio_svc.set_master_volume(level)
    return {"status": "ok"}


@protected_router.post("/audio/mute")
def toggle_audio_mute():
    muted = audio_svc.toggle_master_mute()
    return {"muted": muted}


@protected_router.get("/audio/sessions")
def get_audio_sessions():
    sessions = audio_svc.get_app_sessions()
    for s in sessions:
        _, accent = icon_svc.get_process_icon(s["name"])
        s["accent"] = accent
    return {"sessions": sessions}


@protected_router.post("/audio/sessions/{app_name}/volume")
def set_audio_session_volume(app_name: str, level: int = Body(..., embed=True)):
    audio_svc.set_app_volume(app_name, level)
    return {"status": "ok"}


@protected_router.post("/audio/sessions/{app_name}/mute")
def toggle_audio_session_mute(app_name: str):
    muted = audio_svc.toggle_app_mute(app_name)
    return {"muted": muted}


@protected_router.get("/media/now-playing")
def get_now_playing():
    return media_svc.get_now_playing()


@protected_router.post("/media/{action}")
def send_media_keys(action: str):
    keyboard_svc.send_media(action)
    return {"status": "ok"}


# --- OBS Studio ---

@protected_router.get("/obs/status")
async def get_obs_status():
    return obs_svc.obs_service.get_state()


@protected_router.post("/obs/connect")
async def connect_obs(body: Dict[str, Any] = Body(default={})):
    ok = await obs_svc.obs_service.connect(
        host=body.get("host"),
        port=body.get("port"),
        password=body.get("password"),
    )
    return {"connected": ok, "state": obs_svc.obs_service.get_state()}


@protected_router.post("/obs/disconnect")
async def disconnect_obs():
    await obs_svc.obs_service.disconnect()
    return {"status": "ok"}


@protected_router.post("/obs/launch")
def launch_obs():
    ok = obs_svc.obs_service.launch_obs()
    return {"launched": ok}


@protected_router.post("/obs/stream/toggle")
async def toggle_obs_stream():
    active = await obs_svc.obs_service.toggle_stream()
    return {"streaming": active}


@protected_router.post("/obs/record/toggle")
async def toggle_obs_record():
    active = await obs_svc.obs_service.toggle_record()
    return {"recording": active}


@protected_router.post("/obs/record/pause")
async def toggle_obs_record_pause():
    paused = await obs_svc.obs_service.toggle_record_pause()
    return {"paused": paused}


@protected_router.post("/obs/virtualcam/toggle")
async def toggle_obs_virtualcam():
    active = await obs_svc.obs_service.toggle_virtual_cam()
    return {"virtual_cam": active}


@protected_router.post("/obs/replay/toggle")
async def toggle_obs_replay():
    active = await obs_svc.obs_service.toggle_replay_buffer()
    return {"replay_buffer": active}


@protected_router.post("/obs/replay/save")
async def save_obs_replay():
    saved = await obs_svc.obs_service.save_replay_buffer()
    return {"saved": saved}


@protected_router.post("/obs/studiomode/toggle")
async def toggle_obs_studiomode():
    active = await obs_svc.obs_service.toggle_studio_mode()
    return {"studio_mode": active}


@protected_router.post("/obs/transition")
async def trigger_obs_transition():
    ok = await obs_svc.obs_service.trigger_studio_transition()
    return {"status": "ok" if ok else "failed"}


@protected_router.post("/obs/scene")
async def set_obs_scene(scene: str = Body(..., embed=True)):
    ok = await obs_svc.obs_service.set_scene(scene)
    return {"status": "ok" if ok else "failed"}


@protected_router.post("/obs/input/mute")
async def toggle_obs_input_mute(name: str = Body(..., embed=True)):
    muted = await obs_svc.obs_service.toggle_input_mute(name)
    return {"name": name, "muted": muted}


@protected_router.post("/obs/input/volume")
async def set_obs_input_volume(name: str = Body(..., embed=True), volume: float = Body(..., embed=True)):
    ok = await obs_svc.obs_service.set_input_volume(name, volume)
    return {"status": "ok" if ok else "failed"}


@protected_router.post("/obs/item/toggle")
async def toggle_obs_item(
    id: int = Body(..., embed=True),
    enabled: bool = Body(..., embed=True),
    scene: Optional[str] = Body(None, embed=True),
):
    ok = await obs_svc.obs_service.toggle_scene_item(scene, id, enabled)
    return {"status": "ok" if ok else "failed"}


@protected_router.post("/obs/browser/refresh")
async def refresh_obs_browser_sources():
    refreshed = await obs_svc.obs_service.refresh_browser_sources()
    return {"refreshed": refreshed}


# --- Power ---

@protected_router.post("/power/{action}")
def execute_power_action(action: str, confirm: bool = Body(..., embed=True)):
    if not confirm:
        raise HTTPException(status_code=400, detail="Action requires confirmation")

    actions = {
        "lock": power_svc.lock_workstation,
        "sleep": power_svc.sleep_pc,
        "shutdown": power_svc.shutdown_pc,
        "restart": power_svc.restart_pc,
        "cancel": power_svc.cancel_shutdown,
    }

    if action not in actions:
        raise HTTPException(status_code=404, detail="Power action not found")

    actions[action]()
    return {"status": "ok"}


# --- Stats ---

@protected_router.get("/stats")
def get_stats():
    return stats_svc.get_system_stats()


# Include protected routes into the main router
router.include_router(protected_router)

import threading
import queue
import warnings
from comtypes import CoInitialize
from pycaw.pycaw import AudioUtilities
from pycaw.constants import DEVICE_STATE

# Silence harmless pycaw property-store warnings on virtual/driver audio endpoints (e.g. ASUS Sonic Studio / Bluetooth)
warnings.filterwarnings(
    "ignore",
    message=r"COMError attempting to get property.*",
    category=UserWarning,
)

_audio_queue = queue.Queue()

def _audio_worker():
    # Initialize COM for this background thread
    CoInitialize()
    while True:
        task = _audio_queue.get()
        if task is None:
            break
        func, args, kwargs, result_queue = task
        try:
            res = func(*args, **kwargs)
            result_queue.put(("OK", res))
        except Exception as e:
            result_queue.put(("ERR", e))
        finally:
            _audio_queue.task_done()

_worker_thread = threading.Thread(target=_audio_worker, daemon=True, name="AudioCOMThread")
_worker_thread.start()

def _run_in_audio_thread(func, *args, **kwargs):
    result_queue = queue.Queue()
    _audio_queue.put((func, args, kwargs, result_queue))
    status, res = result_queue.get()
    if status == "ERR":
        print(f"Audio Error in {func.__name__}: {res}")
        # Return a safe fallback based on function name or just raise
        return None
    return res

# --- Internal Implementations (run only on the audio thread) ---

def _get_volume_interface():
    devices = AudioUtilities.GetSpeakers()
    return devices.EndpointVolume

def _get_master_volume():
    try:
        volume = _get_volume_interface()
        level = round(volume.GetMasterVolumeLevelScalar() * 100)
        muted = bool(volume.GetMute())
        return {"level": level, "muted": muted}
    except Exception as e:
        print(f"Error reading volume: {e}")
        return {"level": 0, "muted": False}

def _set_master_volume(level: int):
    try:
        volume = _get_volume_interface()
        scalar = max(0, min(100, level)) / 100.0
        volume.SetMasterVolumeLevelScalar(scalar, None)
    except Exception as e:
        print(f"Error setting volume: {e}")

def _toggle_master_mute():
    try:
        volume = _get_volume_interface()
        current_mute = volume.GetMute()
        new_mute = not current_mute
        volume.SetMute(new_mute, None)
        return bool(new_mute)
    except Exception as e:
        print(f"Error toggling mute: {e}")
        return False

def _get_all_sessions_across_devices():
    import comtypes
    from pycaw.pycaw import AudioUtilities, AudioSession
    sessions = []
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            devices = AudioUtilities.GetAllDevices(device_state=DEVICE_STATE.ACTIVE.value)
        for device in devices:
            if getattr(device.state, 'value', device.state) != 1:  # 1 is Active
                continue
            try:
                manager = device.AudioSessionManager
                if not manager: continue
                enumerator = manager.GetSessionEnumerator()
                for i in range(enumerator.GetCount()):
                    ctl = enumerator.GetSession(i)
                    if ctl:
                        # Pycaw AudioSession wrapper
                        import pycaw.pycaw
                        # Access private method to query IAudioSessionControl2
                        ctl2 = ctl.QueryInterface(pycaw.pycaw.IAudioSessionControl2)
                        if ctl2:
                            sessions.append(AudioSession(ctl2))
            except Exception:
                pass
    except Exception as e:
        print(f"Error enumerating devices: {e}")
    return sessions

def _get_app_sessions():
    from server.services import icon_svc
    sessions = _get_all_sessions_across_devices()
    app_dict = {}
    for session in sessions:
        if session.Process:
            try:
                name = session.Process.name().replace(".exe", "")
                try:
                    exe_path = session.Process.exe()
                    if exe_path:
                        icon_svc.register_process_exe(name, exe_path)
                except Exception:
                    pass
                if session.SimpleAudioVolume:
                    vol = session.SimpleAudioVolume
                    level = round(vol.GetMasterVolume() * 100)
                    muted = bool(vol.GetMute())
                    app_dict[name] = {
                        "id": name,
                        "name": name,
                        "level": level,
                        "muted": muted,
                        "icon_url": f"/api/icons/process/{name}"
                    }
            except Exception:
                pass
    return list(app_dict.values())

def _set_app_volume(app_name: str, level: int):
    sessions = _get_all_sessions_across_devices()
    scalar = max(0, min(100, level)) / 100.0
    for session in sessions:
        if session.Process:
            try:
                if session.Process.name().replace(".exe", "").lower() == app_name.lower():
                    if session.SimpleAudioVolume:
                        session.SimpleAudioVolume.SetMasterVolume(scalar, None)
            except Exception:
                pass

def _toggle_app_mute(app_name: str):
    sessions = _get_all_sessions_across_devices()
    new_mute_state = False
    first = True
    for session in sessions:
        if session.Process:
            try:
                if session.Process.name().replace(".exe", "").lower() == app_name.lower():
                    if session.SimpleAudioVolume:
                        if first:
                            current = session.SimpleAudioVolume.GetMute()
                            new_mute_state = not current
                            first = False
                        session.SimpleAudioVolume.SetMute(new_mute_state, None)
            except Exception:
                pass
    return new_mute_state

# --- Public API (can be called from any thread) ---

def get_master_volume() -> dict:
    res = _run_in_audio_thread(_get_master_volume)
    return res if res is not None else {"level": 0, "muted": False}

def set_master_volume(level: int):
    _run_in_audio_thread(_set_master_volume, level)

def toggle_master_mute() -> bool:
    res = _run_in_audio_thread(_toggle_master_mute)
    return res if res is not None else False

def get_app_sessions() -> list:
    res = _run_in_audio_thread(_get_app_sessions)
    return res if res is not None else []

def set_app_volume(app_name: str, level: int):
    _run_in_audio_thread(_set_app_volume, app_name, level)

def toggle_app_mute(app_name: str) -> bool:
    res = _run_in_audio_thread(_toggle_app_mute, app_name)
    return res if res is not None else False

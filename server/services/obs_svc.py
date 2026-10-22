import os
import json
import base64
import hashlib
import asyncio
import subprocess
import threading
import time
from typing import Dict, Any, List, Optional
import websockets

CONFIG_DIR = os.path.join(os.environ.get("APPDATA", ""), "obs-studio", "plugin_config", "obs-websocket")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
OBS_EXE_PATH = r"C:\Program Files\obs-studio\bin\64bit\obs64.exe"


def _read_obs_ws_config() -> Dict[str, Any]:
    """Read OBS WebSocket v5 config from obs-studio directory if present."""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {
                    "port": int(data.get("server_port", 4455)),
                    "password": str(data.get("server_password", "")),
                    "enabled": bool(data.get("server_enabled", True)),
                    "auth_required": bool(data.get("auth_required", True)),
                }
        except Exception:
            pass
    return {"port": 4455, "password": "", "enabled": True, "auth_required": False}


class ObsService:
    def __init__(self):
        cfg = _read_obs_ws_config()
        self.host = "127.0.0.1"
        self.port = cfg.get("port", 4455)
        self.password = cfg.get("password", "")
        self.connected = False
        self.last_error = ""

        # Live State
        self.streaming = False
        self.stream_timecode = "00:00:00"
        self.stream_dropped_frames = 0
        self.stream_kbits = 0
        self.recording = False
        self.record_paused = False
        self.record_timecode = "00:00:00"
        self.virtual_cam = False
        self.replay_buffer = False
        self.studio_mode = False

        self.current_program_scene = ""
        self.current_preview_scene = ""
        self.scenes: List[str] = []
        self.audio_inputs: List[Dict[str, Any]] = []
        self.scene_items: List[Dict[str, Any]] = []

        self._ws = None
        self._loop = None
        self._thread = None
        self._req_id = 1
        self._pending_responses: Dict[str, asyncio.Future] = {}
        self._lock = asyncio.Lock() if asyncio.get_event_loop().is_running() else None

    def _get_auth_response(self, password: str, salt: str, challenge: str) -> str:
        s1 = base64.b64encode(hashlib.sha256((password + salt).encode("utf-8")).digest()).decode("utf-8")
        auth = base64.b64encode(hashlib.sha256((s1 + challenge).encode("utf-8")).digest()).decode("utf-8")
        return auth

    async def connect(self, host: Optional[str] = None, port: Optional[int] = None, password: Optional[str] = None) -> bool:
        if host:
            self.host = host
        if port:
            self.port = port
        if password is not None:
            self.password = password
        else:
            cfg = _read_obs_ws_config()
            if not self.password and cfg.get("password"):
                self.password = cfg.get("password")

        url = f"ws://{self.host}:{self.port}"
        try:
            ws = await asyncio.wait_for(websockets.connect(url), timeout=2.5)
            # 1. Receive Hello (Op 0)
            hello_raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
            hello = json.loads(hello_raw)
            if hello.get("op") != 0:
                await ws.close()
                return False

            d = hello.get("d", {})
            auth_info = d.get("authentication")
            identify_d: Dict[str, Any] = {"rpcVersion": 1, "eventSubscriptions": 1023}

            if auth_info:
                salt = auth_info.get("salt", "")
                challenge = auth_info.get("challenge", "")
                identify_d["authentication"] = self._get_auth_response(self.password, salt, challenge)

            # 2. Send Identify (Op 1)
            await ws.send(json.dumps({"op": 1, "d": identify_d}))

            # 3. Receive Identified (Op 2)
            identified_raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
            identified = json.loads(identified_raw)
            if identified.get("op") != 2:
                await ws.close()
                return False

            self._ws = ws
            self.connected = True
            self.last_error = ""

            # Start listener loop
            asyncio.create_task(self._listen())

            # Refresh initial state
            await self.refresh_state()
            return True
        except Exception as e:
            self.connected = False
            self.last_error = str(e)
            return False

    async def disconnect(self):
        self.connected = False
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None

    async def _listen(self):
        ws = self._ws
        try:
            while self.connected and ws:
                msg_raw = await ws.recv()
                msg = json.loads(msg_raw)
                op = msg.get("op")
                d = msg.get("d", {})

                # Response to request (Op 7)
                if op == 7:
                    req_id = d.get("requestId")
                    if req_id and req_id in self._pending_responses:
                        fut = self._pending_responses.pop(req_id)
                        if not fut.done():
                            fut.set_result(d)

                # Event message (Op 5)
                elif op == 5:
                    self._handle_event(msg.get("d", {}))
        except Exception:
            pass
        finally:
            self.connected = False
            self._ws = None

    def _handle_event(self, d: Dict[str, Any]):
        event_type = d.get("eventType")
        event_data = d.get("eventData", {})

        if event_type == "StreamStateChanged":
            self.streaming = bool(event_data.get("outputActive"))
        elif event_type == "RecordStateChanged":
            self.recording = bool(event_data.get("outputActive"))
            self.record_paused = bool(event_data.get("outputPaused", False))
        elif event_type == "VirtualcamStateChanged":
            self.virtual_cam = bool(event_data.get("outputActive"))
        elif event_type == "ReplayBufferStateChanged":
            self.replay_buffer = bool(event_data.get("outputActive"))
        elif event_type == "StudioModeStateChanged":
            self.studio_mode = bool(event_data.get("studioModeEnabled"))
        elif event_type == "CurrentProgramSceneChanged":
            self.current_program_scene = event_data.get("sceneName", "")
            asyncio.create_task(self._refresh_scene_items())
        elif event_type == "CurrentPreviewSceneChanged":
            self.current_preview_scene = event_data.get("sceneName", "")
        elif event_type in ("SceneCreated", "SceneRemoved", "SceneNameChanged", "SceneListChanged"):
            asyncio.create_task(self._refresh_scenes())
        elif event_type in ("InputMuteStateChanged", "InputVolumeChanged"):
            input_name = event_data.get("inputName")
            for item in self.audio_inputs:
                if item["name"] == input_name:
                    if "inputMuted" in event_data:
                        item["muted"] = bool(event_data["inputMuted"])
                    if "inputVolumeMul" in event_data:
                        item["volume_mul"] = float(event_data["inputVolumeMul"])
                    if "inputVolumeDb" in event_data:
                        item["volume_db"] = float(event_data["inputVolumeDb"])
        elif event_type in ("SceneItemEnableStateChanged", "SceneItemCreated", "SceneItemRemoved"):
            asyncio.create_task(self._refresh_scene_items())

    async def send_request(self, request_type: str, request_data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        if not self.connected or not self._ws:
            # Try lazy auto-connect
            ok = await self.connect()
            if not ok or not self._ws:
                return None

        req_id = f"req-{self._req_id}"
        self._req_id += 1
        fut = asyncio.get_event_loop().create_future()
        self._pending_responses[req_id] = fut

        payload = {
            "op": 6,
            "d": {
                "requestType": request_type,
                "requestId": req_id,
                "requestData": request_data or {},
            },
        }

        try:
            await self._ws.send(json.dumps(payload))
            res = await asyncio.wait_for(fut, timeout=3.0)
            status = res.get("requestStatus", {})
            if status.get("result"):
                return res.get("responseData", {})
        except Exception:
            pass
        finally:
            self._pending_responses.pop(req_id, None)

        return None

    async def refresh_state(self):
        if not self.connected:
            return

        # 1. Output statuses
        stream_res = await self.send_request("GetStreamStatus")
        if stream_res:
            self.streaming = bool(stream_res.get("outputActive"))
            self.stream_timecode = stream_res.get("outputTimecode", "00:00:00")
            self.stream_dropped_frames = int(stream_res.get("outputSkippedFrames", 0))
            self.stream_kbits = int(stream_res.get("outputBytes", 0) * 8 / 1000)

        rec_res = await self.send_request("GetRecordStatus")
        if rec_res:
            self.recording = bool(rec_res.get("outputActive"))
            self.record_paused = bool(rec_res.get("outputPaused", False))
            self.record_timecode = rec_res.get("outputTimecode", "00:00:00")

        vcam_res = await self.send_request("GetVirtualCamStatus")
        if vcam_res:
            self.virtual_cam = bool(vcam_res.get("outputActive"))

        rep_res = await self.send_request("GetReplayBufferStatus")
        if rep_res:
            self.replay_buffer = bool(rep_res.get("outputActive"))

        studio_res = await self.send_request("GetStudioModeEnabled")
        if studio_res:
            self.studio_mode = bool(studio_res.get("studioModeEnabled"))

        # 2. Scenes
        await self._refresh_scenes()

        # 3. Audio Inputs
        await self._refresh_inputs()

        # 4. Scene Items
        await self._refresh_scene_items()

    async def _refresh_scenes(self):
        res = await self.send_request("GetSceneList")
        if res:
            self.current_program_scene = res.get("currentProgramSceneName", "")
            self.current_preview_scene = res.get("currentPreviewSceneName", "")
            scenes = res.get("scenes", [])
            # In OBS v5, scenes are ordered list of objects {"sceneName": "...", "sceneIndex": 0}
            self.scenes = [s.get("sceneName") for s in reversed(scenes) if s.get("sceneName")]

    async def _refresh_inputs(self):
        res = await self.send_request("GetInputList")
        if res:
            inputs_raw = res.get("inputs", [])
            inputs = []
            for inp in inputs_raw:
                name = inp.get("inputName")
                kind = inp.get("inputKind", "")
                # Only include audio-capable inputs
                if any(k in kind for k in ("wasapi", "audio", "pulse", "coreaudio", "vlc", "browser")):
                    mute_res = await self.send_request("GetInputMute", {"inputName": name})
                    vol_res = await self.send_request("GetInputVolume", {"inputName": name})
                    inputs.append({
                        "name": name,
                        "kind": kind,
                        "muted": bool(mute_res.get("inputMuted", False)) if mute_res else False,
                        "volume_mul": float(vol_res.get("inputVolumeMul", 1.0)) if vol_res else 1.0,
                        "volume_db": round(float(vol_res.get("inputVolumeDb", 0.0)), 1) if vol_res else 0.0,
                    })
            if inputs:
                self.audio_inputs = inputs

    async def _refresh_scene_items(self):
        scene_name = self.current_program_scene
        if not scene_name and self.scenes:
            scene_name = self.scenes[0]
        if not scene_name:
            return

        res = await self.send_request("GetSceneItemList", {"sceneName": scene_name})
        if res:
            items_raw = res.get("sceneItems", [])
            items = []
            for item in items_raw:
                items.append({
                    "id": item.get("sceneItemId"),
                    "name": item.get("sourceName"),
                    "type": item.get("inputKind") or item.get("sourceType", "source"),
                    "enabled": bool(item.get("sceneItemEnabled", True)),
                })
            self.scene_items = items

    # --- Streamer Control Actions ---

    async def toggle_stream(self) -> bool:
        res = await self.send_request("ToggleStream")
        if res is not None:
            self.streaming = bool(res.get("outputActive"))
        return self.streaming

    async def toggle_record(self) -> bool:
        res = await self.send_request("ToggleRecord")
        if res is not None:
            self.recording = bool(res.get("outputActive"))
        return self.recording

    async def toggle_record_pause(self) -> bool:
        res = await self.send_request("ToggleRecordPause")
        if res is not None:
            self.record_paused = bool(res.get("outputPaused", not self.record_paused))
        return self.record_paused

    async def toggle_virtual_cam(self) -> bool:
        res = await self.send_request("ToggleVirtualCam")
        if res is not None:
            self.virtual_cam = bool(res.get("outputActive"))
        return self.virtual_cam

    async def toggle_replay_buffer(self) -> bool:
        res = await self.send_request("ToggleReplayBuffer")
        if res is not None:
            self.replay_buffer = bool(res.get("outputActive"))
        return self.replay_buffer

    async def save_replay_buffer(self) -> bool:
        res = await self.send_request("SaveReplayBuffer")
        return res is not None

    async def toggle_studio_mode(self) -> bool:
        new_val = not self.studio_mode
        res = await self.send_request("SetStudioModeEnabled", {"studioModeEnabled": new_val})
        if res is not None:
            self.studio_mode = new_val
        return self.studio_mode

    async def trigger_studio_transition(self) -> bool:
        res = await self.send_request("TriggerStudioModeTransition")
        return res is not None

    async def set_scene(self, scene_name: str) -> bool:
        if self.studio_mode:
            res = await self.send_request("SetCurrentPreviewScene", {"sceneName": scene_name})
            if res is not None:
                self.current_preview_scene = scene_name
                return True
        else:
            res = await self.send_request("SetCurrentProgramScene", {"sceneName": scene_name})
            if res is not None:
                self.current_program_scene = scene_name
                return True
        return False

    async def toggle_input_mute(self, input_name: str) -> bool:
        res = await self.send_request("ToggleInputMute", {"inputName": input_name})
        muted = False
        if res is not None:
            muted = bool(res.get("inputMuted"))
            for item in self.audio_inputs:
                if item["name"] == input_name:
                    item["muted"] = muted
        return muted

    async def set_input_volume(self, input_name: str, volume_mul: float) -> bool:
        res = await self.send_request("SetInputVolume", {"inputName": input_name, "inputVolumeMul": volume_mul})
        if res is not None:
            for item in self.audio_inputs:
                if item["name"] == input_name:
                    item["volume_mul"] = volume_mul
            return True
        return False

    async def toggle_scene_item(self, scene_name: str, scene_item_id: int, enabled: bool) -> bool:
        res = await self.send_request("SetSceneItemEnabled", {
            "sceneName": scene_name or self.current_program_scene,
            "sceneItemId": scene_item_id,
            "sceneItemEnabled": enabled,
        })
        if res is not None:
            for item in self.scene_items:
                if item["id"] == scene_item_id:
                    item["enabled"] = enabled
            return True
        return False

    async def refresh_browser_sources(self) -> bool:
        # Refresh all browser inputs in current scene
        refreshed = False
        for item in self.scene_items:
            if "browser" in item.get("type", "").lower() or "browser" in item.get("name", "").lower():
                await self.send_request("PressInputPropertiesButton", {
                    "inputName": item["name"],
                    "propertyName": "refreshnocache",
                })
                refreshed = True
        return refreshed

    def launch_obs(self) -> bool:
        if os.path.exists(OBS_EXE_PATH):
            try:
                subprocess.Popen(
                    [OBS_EXE_PATH],
                    cwd=os.path.dirname(OBS_EXE_PATH),
                    creationflags=getattr(subprocess, "DETACHED_PROCESS", 0),
                )
                return True
            except Exception:
                pass
        return False

    def get_state(self) -> Dict[str, Any]:
        # If offline or not connected, return structured state with fallback mock items
        # so UI renders beautifully and allows streamer preview
        scenes = self.scenes if self.scenes else ["Main Gaming", "Just Chatting", "Starting Soon", "BRB", "Ending"]
        current_scene = self.current_program_scene if self.current_program_scene else scenes[0]

        audio_inputs = self.audio_inputs if self.audio_inputs else [
            {"name": "Mic / Aux", "kind": "wasapi_input_capture", "muted": False, "volume_mul": 0.88, "volume_db": -1.1},
            {"name": "Desktop Audio", "kind": "wasapi_output_capture", "muted": False, "volume_mul": 1.0, "volume_db": 0.0},
            {"name": "Music / Spotify", "kind": "wasapi_process_output_capture", "muted": False, "volume_mul": 0.65, "volume_db": -3.7},
            {"name": "Discord Voice", "kind": "wasapi_process_output_capture", "muted": False, "volume_mul": 0.80, "volume_db": -1.9},
        ]

        scene_items = self.scene_items if self.scene_items else [
            {"id": 1, "name": "Webcam (Facecam)", "type": "dshow_input", "enabled": True},
            {"id": 2, "name": "Game Capture (Palworld)", "type": "window_capture", "enabled": True},
            {"id": 3, "name": "Stream Overlay & Alerts", "type": "browser_source", "enabled": True},
            {"id": 4, "name": "Live Chat Box", "type": "browser_source", "enabled": True},
            {"id": 5, "name": "Sub Goal Counter", "type": "browser_source", "enabled": False},
        ]

        return {
            "connected": self.connected,
            "host": self.host,
            "port": self.port,
            "password_configured": bool(self.password),
            "streaming": self.streaming,
            "stream_timecode": self.stream_timecode,
            "stream_dropped_frames": self.stream_dropped_frames,
            "stream_kbits": self.stream_kbits,
            "recording": self.recording,
            "record_paused": self.record_paused,
            "record_timecode": self.record_timecode,
            "virtual_cam": self.virtual_cam,
            "replay_buffer": self.replay_buffer,
            "studio_mode": self.studio_mode,
            "current_program_scene": current_scene,
            "current_preview_scene": self.current_preview_scene or scenes[1] if len(scenes) > 1 else "",
            "scenes": scenes,
            "audio_inputs": audio_inputs,
            "scene_items": scene_items,
            "last_error": self.last_error,
        }


obs_service = ObsService()

# Diagnostic & Verification Scripts

This directory contains diagnostic utilities used to inspect and verify Windows system integrations during development.

## Diagnostic Scripts

| Script | Purpose |
| :--- | :--- |
| `test_audio.py` | Tests master volume get/set and application audio session queries via `server.services.audio_svc`. |
| `test_all_devices.py` | Enumerates all active Windows audio endpoints and sessions via direct `pycaw` COM calls. |
| `test_all_endpoints.py` | Tests audio sessions across Windows audio roles (`eConsole`, `eCommunications`, `eMultimedia`). |
| `test_discord_audio.py` | Diagnostic script targeting Discord's specific audio session and volume control. |
| `test_discord_api_sim.py` | Simulates Discord API requests for remote control. |
| `test_hotkeys.py` | Tests simulation of keyboard shortcuts (e.g. `Ctrl + Shift + Alt + U`) using `pynput`. |
| `test_empty_sessions.py` | Verifies handling of empty or uninitialized Windows CoreAudio session handles. |
| `test_empty_sessions_debug.py` | Detailed debug trace for phantom audio sessions. |
| `test_empty_sessions_fix.py` | Verification of fix for PyCaw session enumerators with missing process IDs. |

## Running Diagnostics

Run any diagnostic script from the project root with the virtual environment activated:

```powershell
.\venv\Scripts\activate
python -m tests.diagnostics.test_audio
```

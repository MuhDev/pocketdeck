import os
import subprocess
import webbrowser
from server.config import settings

def launch_preset(preset_id: str) -> bool:
    """Launches a preset by ID defined in the configuration."""
    preset = next((p for p in settings.presets if p.id == preset_id), None)
    if not preset:
        print(f"Preset {preset_id} not found.")
        return False
        
    try:
        target = os.path.expandvars(preset.target)
        if preset.type == "app":
            args = preset.args or []
            # DETACHED_PROCESS = 0x00000008, prevents it from attaching to server console
            subprocess.Popen([target] + args, shell=False, creationflags=0x00000008)
        elif preset.type == "url":
            webbrowser.open(target)
        elif preset.type in ["folder", "steam"]:
            os.startfile(target)
        elif preset.type == "shell_app":
            subprocess.Popen(["explorer.exe", f"shell:AppsFolder\\{target}"], shell=False)
        return True
    except Exception as e:
        print(f"Error launching preset {preset_id}: {e}")
        return False

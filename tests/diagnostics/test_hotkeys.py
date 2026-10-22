import sys
import os

# Add the project root to sys.path
sys.path.insert(0, os.path.abspath('.'))

from server.services import keyboard_svc

# test pressing ctrl+shift+alt+u
try:
    keyboard_svc.press_hotkey(["ctrl", "shift", "alt", "u"])
    print("hotkey pressed successfully")
except Exception as e:
    print(f"error: {e}")

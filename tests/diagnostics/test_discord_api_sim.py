import sys
import os
import time

sys.path.insert(0, os.path.abspath('.'))

from server.services import audio_svc

print("Current sessions:", audio_svc.get_app_sessions())

print("\nSetting Discord volume to 25%...")
audio_svc.set_app_volume("Discord", 25)
time.sleep(1)

print("\nCurrent sessions after set:", audio_svc.get_app_sessions())

print("\nSetting Discord volume to 75%...")
audio_svc.set_app_volume("Discord", 75)
time.sleep(1)

print("\nCurrent sessions after set:", audio_svc.get_app_sessions())

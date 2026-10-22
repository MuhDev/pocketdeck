import sys
import os

# Add the project root to sys.path
sys.path.insert(0, os.path.abspath('.'))

from server.services import audio_svc

print("Testing master volume...")
print("Current:", audio_svc.get_master_volume())
audio_svc.set_master_volume(50)
print("After set 50:", audio_svc.get_master_volume())

print("\nTesting app sessions...")
sessions = audio_svc.get_app_sessions()
print(sessions)

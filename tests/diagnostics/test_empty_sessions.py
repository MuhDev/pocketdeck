import sys
import os

sys.path.insert(0, os.path.abspath('.'))

from server.services import audio_svc

print("Testing get_app_sessions():")
print(audio_svc.get_app_sessions())

import sys
import os

sys.path.insert(0, os.path.abspath('.'))

from pycaw.pycaw import AudioUtilities
from pycaw.constants import EDataFlow, ERole
from comtypes import CoInitialize, CLSCTX_ALL
from pycaw.pycaw import IAudioSessionManager2

CoInitialize()

def get_sessions_for_role(role):
    try:
        device_enumerator = AudioUtilities.CreateDeviceEnumerator()
        device = device_enumerator.GetDefaultAudioEndpoint(EDataFlow.eRender.value, role.value)
        interface = device.Activate(IAudioSessionManager2._iid_, CLSCTX_ALL, None)
        manager = interface.QueryInterface(IAudioSessionManager2)
        session_enumerator = manager.GetSessionEnumerator()
        sessions = []
        for i in range(session_enumerator.GetCount()):
            sessions.append(session_enumerator.GetSession(i))
        return sessions
    except Exception as e:
        print(f"Error getting sessions for role {role}: {e}")
        return []

print("=== Console (Default) Sessions ===")
sessions_console = get_sessions_for_role(ERole.eConsole)
for s in sessions_console:
    if s.GetSessionIdentifier():
        print(s.GetSessionIdentifier())

print("\n=== Communications Sessions ===")
sessions_comm = get_sessions_for_role(ERole.eCommunications)
for s in sessions_comm:
    if s.GetSessionIdentifier():
        print(s.GetSessionIdentifier())

print("\n=== Multimedia Sessions ===")
sessions_multi = get_sessions_for_role(ERole.eMultimedia)
for s in sessions_multi:
    if s.GetSessionIdentifier():
        print(s.GetSessionIdentifier())

import sys
import os

sys.path.insert(0, os.path.abspath('.'))

from pycaw.pycaw import AudioUtilities
from comtypes import CoInitialize

CoInitialize()
sessions = AudioUtilities.GetAllSessions()
for session in sessions:
    if session.Process:
        try:
            name = session.Process.name()
            if "discord" in name.lower():
                print(f"Found Discord Session: name={name}, exe={session.Process.exe()}")
                if session.SimpleAudioVolume:
                    vol = session.SimpleAudioVolume.GetMasterVolume()
                    print(f"  Current Volume: {vol}")
                    
                    # Try setting it
                    session.SimpleAudioVolume.SetMasterVolume(0.5, None)
                    print("  Successfully set volume to 50%")
        except Exception as e:
            print(f"Error accessing session: {e}")

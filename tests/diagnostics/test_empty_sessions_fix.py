import sys
import os

sys.path.insert(0, os.path.abspath('.'))

import comtypes
comtypes.CoInitialize()
from pycaw.pycaw import AudioUtilities, AudioSession
import pycaw.pycaw

sessions = []
try:
    devices = AudioUtilities.GetAllDevices()
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
                    ctl2 = ctl.QueryInterface(pycaw.pycaw.IAudioSessionControl2)
                    if ctl2:
                        sessions.append(AudioSession(ctl2))
        except Exception as e:
            print(f"Exception on device {device.FriendlyName}: {e}")
except Exception as e:
    print(f"Error enumerating devices: {e}")

print("Sessions found:")
for s in sessions:
    if s.Process:
        print(s.Process.name())

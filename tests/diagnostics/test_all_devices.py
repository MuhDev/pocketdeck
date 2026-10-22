import sys
import os

sys.path.insert(0, os.path.abspath('.'))

import comtypes
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioSessionManager2, AudioSession

comtypes.CoInitialize()
devices = AudioUtilities.GetAllDevices()

for device in devices:
    try:
        if device.state != 1:  # Active
            continue
            
        interface = device.Activate(IAudioSessionManager2._iid_, CLSCTX_ALL, None)
        if interface is None:
            continue
            
        mgr = interface.QueryInterface(IAudioSessionManager2)
        sessionEnumerator = mgr.GetSessionEnumerator()
        count = sessionEnumerator.GetCount()
        
        for i in range(count):
            ctl = sessionEnumerator.GetSession(i)
            if ctl is None:
                continue
            session = AudioSession(ctl)
            if session.Process:
                print(f"Device: {device.FriendlyName} | App: {session.Process.name()} | Vol: {session.SimpleAudioVolume.GetMasterVolume()}")
    except Exception as e:
        pass

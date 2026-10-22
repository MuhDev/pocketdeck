import os
import ctypes

def lock_workstation():
    ctypes.windll.user32.LockWorkStation()

def sleep_pc():
    os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")

def shutdown_pc():
    os.system("shutdown /s /t 5")

def restart_pc():
    os.system("shutdown /r /t 5")

def cancel_shutdown():
    os.system("shutdown /a")

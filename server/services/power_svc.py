import ctypes
import subprocess

# CREATE_NO_WINDOW flag for clean background invocation on Windows
_NO_WINDOW = 0x08000000

def lock_workstation():
    ctypes.windll.user32.LockWorkStation()

def sleep_pc():
    subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], creationflags=_NO_WINDOW, check=False)

def shutdown_pc():
    subprocess.run(["shutdown", "/s", "/t", "5"], creationflags=_NO_WINDOW, check=False)

def restart_pc():
    subprocess.run(["shutdown", "/r", "/t", "5"], creationflags=_NO_WINDOW, check=False)

def cancel_shutdown():
    subprocess.run(["shutdown", "/a"], creationflags=_NO_WINDOW, check=False)

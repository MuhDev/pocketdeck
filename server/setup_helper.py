"""
PocketDeck Setup & Startup Helper
Provides friendly utilities for non-developer setup and launch:
- Desktop shortcut creation (handling OneDrive, custom shell paths, etc.)
- Local network IP detection & terminal QR code
- Automated browser launcher
"""

import os
import sys
import socket
import subprocess
from pathlib import Path


def get_project_root() -> Path:
    """Returns the absolute Path of the project root directory."""
    return Path(__file__).resolve().parent.parent


def ensure_app_icon() -> Path:
    """Returns the path to pocketdeck.ico, generating it from icon-512.png if needed."""
    logo_dir = get_project_root() / "web" / "assets" / "logo"
    ico_path = logo_dir / "pocketdeck.ico"
    png_path = logo_dir / "icon-512.png"
    if not ico_path.exists() and png_path.exists():
        try:
            from PIL import Image
            img = Image.open(png_path).convert("RGBA")
            sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
            img.save(ico_path, format="ICO", sizes=sizes)
        except Exception:
            pass
    return ico_path


def set_console_icon() -> bool:
    """Sets the PocketDeck icon on the active Windows console window and taskbar."""
    if os.name != "nt":
        return False
    try:
        import ctypes
        ico_path = ensure_app_icon()
        if not ico_path.exists():
            return False

        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("PocketDeck.ControlServer")
        except Exception:
            pass

        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if not hwnd:
            return False

        IMAGE_ICON = 1
        LR_LOADFROMFILE = 0x00000010
        WM_SETICON = 0x0080
        ICON_SMALL = 0
        ICON_BIG = 1

        hicon_small = ctypes.windll.user32.LoadImageW(
            None, str(ico_path), IMAGE_ICON, 16, 16, LR_LOADFROMFILE
        )
        hicon_big = ctypes.windll.user32.LoadImageW(
            None, str(ico_path), IMAGE_ICON, 48, 48, LR_LOADFROMFILE
        )

        if hicon_small:
            ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, hicon_small)
        if hicon_big:
            ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, hicon_big)
            try:
                ctypes.windll.kernel32.SetConsoleIcon(hicon_big)
            except Exception:
                pass
        return bool(hicon_small or hicon_big)
    except Exception:
        return False


def is_admin() -> bool:
    """Checks whether the current process has Windows Administrator privileges."""
    if os.name != "nt":
        return True
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def ensure_admin() -> bool:
    """
    Ensures the current process is running with Windows Administrator privileges.
    If not elevated, relaunches via Windows UAC ('runas') and exits the current process.
    Can be bypassed via '--no-admin' CLI flag or POCKETDECK_NO_ADMIN=1 environment variable.
    """
    if os.name != "nt":
        return True
    if "--no-admin" in sys.argv or os.environ.get("POCKETDECK_NO_ADMIN") == "1":
        return is_admin()
    if is_admin():
        return True

    print("[i] Requesting Administrator privileges for PocketDeck...")
    try:
        import ctypes
        root_dir = str(get_project_root())
        run_bat = os.path.join(root_dir, "run.bat")
        if os.path.exists(run_bat):
            ret = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", run_bat, None, root_dir, 1
            )
        else:
            extra_args = " ".join(f'"{a}"' for a in sys.argv[1:])
            params = f"-m server.main {extra_args}".strip()
            ret = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, params, root_dir, 1
            )
        if ret <= 32:
            print("[ERROR] Administrator elevation was declined or failed.")
            sys.exit(1)
        sys.exit(0)
    except SystemExit:
        raise
    except Exception as e:
        print(f"[ERROR] Could not elevate to Administrator: {e}")
        sys.exit(1)


def get_lan_ip() -> str:
    """Detects the active local Wi-Fi or Ethernet IPv4 address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Connect to public DNS address without sending data to resolve active interface
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def create_desktop_shortcut() -> bool:
    """Creates Windows shortcuts (Desktop & project root) pointing to run.bat with the PocketDeck icon and Admin flag."""
    try:
        root_dir = str(get_project_root())
        target_bat = os.path.join(root_dir, "run.bat")
        icon_path = str(ensure_app_icon())
        
        # Use a temporary PowerShell script to query WScript.Shell.SpecialFolders('Desktop')
        # This properly handles OneDrive-redirected Desktops, domain profiles, etc.
        ps_file = os.path.join(root_dir, "data", "_make_shortcut.ps1")
        os.makedirs(os.path.join(root_dir, "data"), exist_ok=True)

        lines = [
            "$ws = New-Object -ComObject WScript.Shell",
            "$desktop = $ws.SpecialFolders.Item('Desktop')",
            "$targets = @(",
            "    (Join-Path $desktop 'PocketDeck.lnk'),",
            "    (Join-Path $args[1] 'PocketDeck.lnk')",
            ")",
            "foreach ($lnkPath in $targets) {",
            "    $s = $ws.CreateShortcut($lnkPath)",
            "    $s.TargetPath = $args[0]",
            "    $s.WorkingDirectory = $args[1]",
            "    $s.Description = 'PocketDeck Control Deck Server (Run as Administrator)'",
            "    if (Test-Path $args[2]) {",
            "        $s.IconLocation = \"$($args[2]),0\"",
            "    }",
            "    $s.Save()",
            "    # Enable 'Run as administrator' flag (SLDF_RUNAS_USER = 0x20 at byte offset 0x15)",
            "    $bytes = [System.IO.File]::ReadAllBytes($lnkPath)",
            "    $bytes[0x15] = $bytes[0x15] -bor 0x20",
            "    [System.IO.File]::WriteAllBytes($lnkPath, $bytes)",
            "}",
            "Write-Output $targets[0]",
        ]
        
        with open(ps_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

        res = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps_file, target_bat, root_dir, icon_path],
            capture_output=True,
            text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            check=False,
        )

        try:
            os.remove(ps_file)
        except Exception:
            pass

        created_path = res.stdout.strip()
        if created_path and os.path.exists(created_path):
            return True

        return False
    except Exception:
        return False


def print_connection_card(port: int = 8765):
    """Prints a clear, friendly connection card with terminal QR code."""
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    lan_ip = get_lan_ip()
    local_url = f"http://localhost:{port}"
    mobile_url = f"http://{lan_ip}:{port}"

    border = "=" * 62
    subborder = "-" * 62

    priv_label = "Administrator (Full Access)" if is_admin() else "Standard User"

    print("\n" + border)
    print("                    🚀 POCKETDECK IS RUNNING")
    print(border)
    print(f"  💻 On this PC:          {local_url}")
    print(f"  📱 On Phone or Tablet:  {mobile_url}")
    print("  🔑 Default PIN:         1234")
    print(f"  🛡️  Privileges:          {priv_label}")
    print(subborder)
    print("  📷 Point your phone's camera at this QR code to connect:")
    print()

    try:
        import qrcode
        qr = qrcode.QRCode(border=1)
        qr.add_data(mobile_url)
        qr.make(fit=True)
        qr.print_ascii(invert=True)
    except Exception:
        print(f"  (Open your phone's browser and go to: {mobile_url})")

    print(subborder)
    print("  ℹ️  Keep this window open while using PocketDeck.")
    print("  ❌ Press Ctrl+C in this window at any time to quit.")
    print(border + "\n")


if __name__ == "__main__":
    if "--create-shortcut" in sys.argv:
        success = create_desktop_shortcut()
        if success:
            print("[OK] Desktop shortcut created successfully!")
        else:
            print("[FAIL] Could not create desktop shortcut.")
    elif "--banner" in sys.argv:
        print_connection_card()

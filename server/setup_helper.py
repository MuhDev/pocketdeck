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
    """Creates a Windows Desktop shortcut pointing to run.bat."""
    try:
        root_dir = str(get_project_root())
        target_bat = os.path.join(root_dir, "run.bat")
        
        # Use a temporary PowerShell script to query WScript.Shell.SpecialFolders('Desktop')
        # This properly handles OneDrive-redirected Desktops, domain profiles, etc.
        ps_file = os.path.join(root_dir, "data", "_make_shortcut.ps1")
        os.makedirs(os.path.join(root_dir, "data"), exist_ok=True)

        lines = [
            "$ws = New-Object -ComObject WScript.Shell",
            "$desktop = $ws.SpecialFolders.Item('Desktop')",
            "$lnkPath = Join-Path $desktop 'PocketDeck.lnk'",
            "$s = $ws.CreateShortcut($lnkPath)",
            "$s.TargetPath = $args[0]",
            "$s.WorkingDirectory = $args[1]",
            "$s.Description = 'PocketDeck Control Deck Server'",
            "$s.Save()",
            "Write-Output $lnkPath",
        ]
        
        with open(ps_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

        res = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps_file, target_bat, root_dir],
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

    print("\n" + border)
    print("                    🚀 POCKETDECK IS RUNNING")
    print(border)
    print(f"  💻 On this PC:          {local_url}")
    print(f"  📱 On Phone or Tablet:  {mobile_url}")
    print("  🔑 Default PIN:         1234")
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

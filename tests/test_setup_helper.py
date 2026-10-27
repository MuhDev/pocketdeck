import os
import socket
from server.setup_helper import get_lan_ip, get_project_root, is_admin, ensure_admin, ensure_app_icon

def test_get_project_root():
    root = get_project_root()
    assert root.exists()
    assert (root / "requirements.txt").exists()
    assert (root / "server").exists()

def test_get_lan_ip():
    ip = get_lan_ip()
    assert isinstance(ip, str)
    # Check that it's a valid IPv4 string
    parts = ip.split(".")
    assert len(parts) == 4
    assert all(p.isdigit() and 0 <= int(p) <= 255 for p in parts)

def test_is_admin_returns_bool():
    result = is_admin()
    assert isinstance(result, bool)

def test_ensure_admin_bypass_env(monkeypatch):
    monkeypatch.setenv("POCKETDECK_NO_ADMIN", "1")
    result = ensure_admin()
    assert isinstance(result, bool)

def test_ensure_app_icon():
    ico_path = ensure_app_icon()
    assert ico_path.exists()
    assert ico_path.suffix == ".ico"

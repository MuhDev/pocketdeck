import socket
from server.setup_helper import get_lan_ip, get_project_root

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

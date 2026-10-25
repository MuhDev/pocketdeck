import pytest
from fastapi.testclient import TestClient
from server.main import app
from server.auth import VALID_TOKENS

client = TestClient(app)

def test_unauthenticated_access_denied():
    res = client.get("/api/apps")
    assert res.status_code == 401
    assert "Invalid authorization header" in res.json()["detail"]

def test_login_invalid_pin():
    res = client.post("/api/auth/login", json={"pin": "invalid_wrong_pin"})
    assert res.status_code == 401
    assert res.json()["detail"] == "Invalid PIN"

def test_stats_authenticated():
    # Insert a dummy test token
    test_token = "pytest_api_test_token_12345"
    VALID_TOKENS.add(test_token)
    try:
        headers = {"Authorization": f"Bearer {test_token}"}
        res = client.get("/api/stats", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert "cpu" in data
        assert "ram" in data
        assert "gpu" in data
    finally:
        VALID_TOKENS.discard(test_token)

def test_apps_list_authenticated():
    test_token = "pytest_api_test_token_apps"
    VALID_TOKENS.add(test_token)
    try:
        headers = {"Authorization": f"Bearer {test_token}"}
        res = client.get("/api/apps", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert "presets" in data
        assert isinstance(data["presets"], list)
        assert "hostname" in data
    finally:
        VALID_TOKENS.discard(test_token)

import asyncio
import pytest
from fastapi import HTTPException
from server.auth import verify_pin, get_token_header, VALID_TOKENS
from server.config import settings

def test_verify_pin_valid():
    # Use default PIN 1234 whose SHA256 matches DEFAULT_PIN_HASH
    token = verify_pin("1234")
    if settings.server.pin_hash == "03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4":
        assert token is not None
        assert token in VALID_TOKENS
        # verify header authentication accepts valid token
        auth_header = f"Bearer {token}"
        resolved = asyncio.run(get_token_header(auth_header))
        assert resolved == token

def test_verify_pin_invalid():
    token = verify_pin("wrong_pin_0000_invalid")
    assert token is None

def test_get_token_header_missing():
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(get_token_header(None))
    assert exc_info.value.status_code == 401

def test_get_token_header_invalid_scheme():
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(get_token_header("Basic 123456"))
    assert exc_info.value.status_code == 401

def test_get_token_header_expired_or_unknown():
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(get_token_header("Bearer non_existent_token_12345"))
    assert exc_info.value.status_code == 401

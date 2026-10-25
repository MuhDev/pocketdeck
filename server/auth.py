import hashlib
import secrets
from fastapi import Header, HTTPException

from server.config import settings

# Store valid tokens in memory
VALID_TOKENS: set[str] = set()

def verify_pin(pin: str) -> str | None:
    """Verifies a PIN against the hash in config and returns a session token if valid."""
    pin_hash = hashlib.sha256(pin.encode()).hexdigest()
    if pin_hash == settings.server.pin_hash:
        token = secrets.token_hex(16)
        VALID_TOKENS.add(token)
        return token
    return None

async def get_token_header(authorization: str | None = Header(None)) -> str:
    """FastAPI dependency to check for a valid Bearer token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    token = authorization.split(" ")[1]
    if token not in VALID_TOKENS:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
        
    return token

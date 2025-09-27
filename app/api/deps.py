import os
from fastapi import Header, HTTPException, status

API_KEY = os.getenv("QTS_API_KEY", "test-api-key")

async def require_api_key(x_api_key: str = Header(default=None)):
    if API_KEY == "test-api-key":
        # dev mode: allow if header missing (easier testing)
        return
    if not x_api_key or x_api_key != API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API key")

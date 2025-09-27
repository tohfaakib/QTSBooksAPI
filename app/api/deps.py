import os
from fastapi import HTTPException, status, Security
from fastapi.security import APIKeyHeader

API_KEY = os.getenv("QTS_API_KEY")

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

async def require_api_key(x_api_key: str = Security(api_key_header)):
    if not API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server API key not configured"
        )
    if not x_api_key or x_api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )

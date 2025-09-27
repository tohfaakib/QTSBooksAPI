from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import os

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None

def get_db() -> AsyncIOMotorDatabase:
    global _client, _db
    if _db is None:
        uri = os.getenv("QTS_MONGODB_URI", "mongodb://localhost:27017")
        name = os.getenv("QTS_MONGODB_DB", "qtsbook")
        _client = AsyncIOMotorClient(uri)
        _db = _client[name]
    return _db

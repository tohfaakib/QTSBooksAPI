from fastapi import APIRouter, Query, Depends
from app.db.mongo import get_db
from app.models.book import Change
from app.api.deps import require_api_key

router = APIRouter(prefix="/changes", tags=["changes"], dependencies=[Depends(require_api_key)])

@router.get("", response_model=list[Change])
async def list_changes(skip: int = 0, limit: int = Query(20, ge=1, le=100)):
    db = get_db()
    cursor = db["changes"].find().sort("changed_at", -1).skip(skip).limit(limit)
    docs = [doc async for doc in cursor]
    for d in docs:
        d["_id"] = str(d["_id"])
    return [Change(**d) for d in docs]

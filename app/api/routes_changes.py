from fastapi import APIRouter, Query, Depends
from typing import Optional, Literal
from datetime import datetime, timezone, timedelta

from app.db.mongo import get_db
from app.models.book import Change
from app.api.deps import require_api_key

router = APIRouter(prefix="/changes", tags=["changes"], dependencies=[Depends(require_api_key)])

@router.get(
    "",
    summary="List change log entries",
    description=(
        "View recent updates (new items and field changes). "
        "Filter by kind (new/update), significance, time window, or URL. "
        "Returns pagination metadata."
    ),
)
async def list_changes(
    kind: Optional[Literal["new", "update"]] = Query(None, description="Filter by change_kind"),
    significant: Optional[bool] = Query(None, description="Only significant changes if true"),
    url: Optional[str] = Query(None, description="Exact URL filter"),
    since_hours: Optional[int] = Query(None, ge=1, description="If set, uses now-<hours> as start"),
    since: Optional[datetime] = Query(None, description="ISO datetime start (UTC)"),
    until: Optional[datetime] = Query(None, description="ISO datetime end (UTC, default now)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    db = get_db()

    # --- build time window (UTC-aware) ---
    now = datetime.now(timezone.utc)
    if since_hours is not None:
        since_dt = now - timedelta(hours=since_hours)
    elif since is not None:
        since_dt = since if since.tzinfo else since.replace(tzinfo=timezone.utc)
    else:
        since_dt = None

    if until is not None:
        until_dt = until if until.tzinfo else until.replace(tzinfo=timezone.utc)
    else:
        until_dt = now

    q: dict = {}
    if since_dt is not None:
        q.setdefault("changed_at", {})["$gte"] = since_dt
    if until_dt is not None:
        q.setdefault("changed_at", {})["$lte"] = until_dt
    if kind is not None:
        q["change_kind"] = kind
    if significant is not None:
        q["significant"] = significant
    if url:
        q["url"] = url

    total = await db["changes"].count_documents(q)
    cursor = db["changes"].find(q).sort("changed_at", -1).skip(skip).limit(limit)
    docs = [doc async for doc in cursor]
    for d in docs:
        d["_id"] = str(d["_id"])
    items = [Change(**d).model_dump(by_alias=True) for d in docs]

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": items,
    }

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Optional, Literal

from fastapi import APIRouter, Query, Depends
from app.db.mongo import get_db
from app.models.book import Change
from app.api.deps import require_api_key
from app.api.limit import rate_limit

router = APIRouter(
    prefix="/changes",
    tags=["changes"],
    dependencies=[Depends(require_api_key), Depends(rate_limit)],
)

@router.get(
    "",
    summary="List change log entries",
    description=(
        "View recent updates (new items and field changes). "
        "Filter by kind (new/update), significance, time window, or URL. "
        "Pagination is page-based (page/page_size)."
    ),
)
async def list_changes(
    kind: Optional[Literal["new", "update"]] = Query(None, description="Filter by change_kind"),
    significant: Optional[bool] = Query(None, description="Only significant changes if true"),
    url: Optional[str] = Query(None, description="Exact URL filter"),
    since_hours: Optional[int] = Query(None, ge=1, description="If set, uses now-<hours> as start"),
    since: Optional[datetime] = Query(None, description="ISO datetime start (UTC)"),
    until: Optional[datetime] = Query(None, description="ISO datetime end (UTC, default now)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
):
    db = get_db()

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
    total_pages = math.ceil(total / page_size) if total else 0
    page = max(1, min(page, max(total_pages, 1)))
    skip = (page - 1) * page_size

    cursor = db["changes"].find(q).sort("changed_at", -1).skip(skip).limit(page_size)
    docs = [doc async for doc in cursor]
    for d in docs:
        d["_id"] = str(d["_id"])
    items = [Change(**d).model_dump(by_alias=True) for d in docs]

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_prev": page > 1,
        "has_next": page < total_pages,
        "prev_page": page - 1 if page > 1 else None,
        "next_page": page + 1 if page < total_pages else None,
        "items": items,
    }

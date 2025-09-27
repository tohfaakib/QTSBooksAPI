import os
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from app.api.deps import require_api_key
from app.api.limit import rate_limit

router = APIRouter(
    prefix="/reports",
    tags=["reports"],
    dependencies=[Depends(require_api_key), Depends(rate_limit)],
)

REPORT_DIR = "reports"

def _today_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")

@router.get("/today", summary="Download today's change report")
def download_today(format: str = Query("json", pattern="^(json|csv)$")):
    stamp = _today_stamp()
    filename = f"changes_{stamp}.{format}"
    path = os.path.join(REPORT_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"No report found for today: {filename}")
    media = "application/json" if format == "json" else "text/csv"
    return FileResponse(path, media_type=media, filename=filename)

@router.get("/list", summary="List available report files")
def list_reports():
    if not os.path.isdir(REPORT_DIR):
        return {"files": []}
    files = sorted(os.listdir(REPORT_DIR))
    return {"files": files}

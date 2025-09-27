import os, json, csv
from datetime import datetime, timedelta, timezone
from typing import Optional

def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def _dt(ts) -> str:
    if isinstance(ts, datetime):
        return ts.astimezone(timezone.utc).isoformat()
    return str(ts)

def generate_change_report(db, since: Optional[datetime] = None, until: Optional[datetime] = None, out_dir: str = "reports") -> dict:
    now = datetime.now(timezone.utc)
    if since is None:
        since = now - timedelta(days=1)
    if until is None:
        until = now

    q = {"changed_at": {"$gte": since, "$lte": until}}
    cur = db["changes"].find(q).sort("changed_at", 1)

    rows = []
    for c in cur:
        rows.append({
            "url": c.get("url"),
            "changed_at": _dt(c.get("changed_at")),
            "change_kind": c.get("change_kind"),
            "significant": bool(c.get("significant")),
            "price_delta": c.get("price_delta"),
            "fields_changed": c.get("fields_changed", {}),
            "prev_hash": c.get("prev_hash"),
            "new_hash": c.get("new_hash"),
        })

    _ensure_dir(out_dir)
    stamp = now.strftime("%Y-%m-%d")
    json_path = os.path.join(out_dir, f"changes_{stamp}.json")
    csv_path  = os.path.join(out_dir, f"changes_{stamp}.csv")

    # JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"from": _dt(since), "to": _dt(until), "count": len(rows), "items": rows}, f, ensure_ascii=False, indent=2)

    # CSV
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["url","changed_at","change_kind","significant","price_delta","fields_changed"])
        for r in rows:
            w.writerow([r["url"], r["changed_at"], r["change_kind"], r["significant"], r["price_delta"], json.dumps(r["fields_changed"], ensure_ascii=False)])

    return {"json_path": json_path, "csv_path": csv_path, "count": len(rows)}

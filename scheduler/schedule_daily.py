import os
import sys
import asyncio
import subprocess
from zoneinfo import ZoneInfo
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from typing import Optional
from pymongo import MongoClient
from datetime import datetime, timezone, timedelta

from app.utils.report import generate_change_report
from app.utils.alerts import build_change_summary, send_email_alert



REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

TZ = ZoneInfo(os.getenv("QTS_TIMEZONE", "Asia/Dhaka"))
SCRAPY_ROOT = os.path.join(REPO_ROOT, "app", "crawler")

def run_crawl_blocking():
    env = os.environ.copy()
    env.setdefault("QTS_MONGODB_URI", "mongodb://mongo:27017")
    env.setdefault("QTS_MONGODB_DB", "qtsbook")
    env.setdefault("QTS_LOG_LEVEL", "INFO")

    subprocess.run(
        ["scrapy", "crawl", "books", "-L", env["QTS_LOG_LEVEL"]],
        cwd=SCRAPY_ROOT,
        check=True,
        env=env,
    )

async def run_once():
    # scrape
    await asyncio.to_thread(run_crawl_blocking)
    # report
    await asyncio.to_thread(build_daily_report_blocking)


def main():
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(REPO_ROOT, ".env"))
    except Exception:
        pass

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    scheduler = AsyncIOScheduler(timezone=TZ, event_loop=loop)
    # Daily at 09:00 AM
    scheduler.add_job(run_once, "cron", hour=9, minute=0, id="daily_crawl")
    # scheduler.add_job(run_once, "cron", minute="*/1", id="minutely_test")

    print(f"[{datetime.now(TZ).isoformat()}] Scheduler started (daily @ 09:00). Ctrl+C to stop.")
    scheduler.start()
    try:
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        loop.close()


def _format_summary(summary: dict) -> str:
    lines = [
        f"Since: {summary['since']}",
        f"Total: {summary['total']}",
        f"New: {summary['new']}",
        f"Updated: {summary['updated']}",
        f"Significant: {summary['significant']}",
    ]
    if summary["significant_sample"]:
        lines.append("Recent significant:")
        for s in summary["significant_sample"]:
            lines.append(f"  • {s['url']} [{s['fields']}]")
    return "\n".join(lines)

def _as_aware_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _get_db_sync():
    uri = os.getenv("QTS_MONGODB_URI", "mongodb://mongo:27017")
    db_name = os.getenv("QTS_MONGODB_DB", "qtsbook")
    client = MongoClient(uri, tz_aware=True, tzinfo=timezone.utc)
    return client, client[db_name]

def _get_last_notified_at(db):
    meta = db["meta"].find_one({"_k": "alerts"}, {"last_notified_at": 1})
    return _as_aware_utc(meta.get("last_notified_at")) if meta else None

def _set_last_notified_at(db, ts: datetime):
    db["meta"].update_one(
        {"_k": "alerts"},
        {"$set": {"last_notified_at": ts}},
        upsert=True
    )

def _most_recent_change_at(db):
    doc = db["changes"].find({}, {"changed_at": 1}).sort("changed_at", -1).limit(1)
    doc = next(doc, None)
    return _as_aware_utc(doc.get("changed_at")) if doc else None

def build_daily_report_blocking():
    client, db = _get_db_sync()

    try:
        now = datetime.now(timezone.utc)
        last_notified = _get_last_notified_at(db)
        since = last_notified or (now - timedelta(days=1))

        new_count = db["changes"].count_documents({"changed_at": {"$gt": since}})

        report = generate_change_report(db, since=since, until=now, out_dir="reports")

        hours = max(1, int((now - since).total_seconds() // 3600))
        summary = build_change_summary(db, since_hours=hours)

        text = (
            f"Daily change report ready.\n"
            f"JSON: {report['json_path']}\nCSV: {report['csv_path']}\n\n"
            f"Since: {summary['since']}\n"
            f"Total: {summary['total']}\nNew: {summary['new']}\n"
            f"Updated: {summary['updated']}\nSignificant: {summary['significant']}\n"
        )
        print(f"[scheduler] {text.replace(os.linesep, ' | ')}")

        if new_count > 0:
            ok, msg = send_email_alert(
                subject=f"[QTS] Changes: sig={summary['significant']} new={summary['new']}",
                body=text,
            )
            print(f"[scheduler] Alert: {msg}")

            latest = _most_recent_change_at(db)
            if latest:
                _set_last_notified_at(db, latest)

    finally:
        client.close()


if __name__ == "__main__":
    main()

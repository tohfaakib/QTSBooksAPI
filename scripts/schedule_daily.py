# scripts/schedule_daily.py
import os
import sys
import asyncio
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# --- ensure repo root is importable (for module runs, logs, etc.) ---
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
# -------------------------------------------------------------------

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
    await asyncio.to_thread(run_crawl_blocking)

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

    print(f"[{datetime.now(TZ).isoformat()}] Scheduler started (daily @ 09:00). Ctrl+C to stop.")
    scheduler.start()
    try:
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        loop.close()

if __name__ == "__main__":
    main()

from __future__ import annotations

import os
import subprocess
import asyncio
from collections import deque
from typing import Optional
from pathlib import Path
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response, PlainTextResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from secrets import compare_digest

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
templates = Jinja2Templates(directory="app/templates")
basic = HTTPBasic()

_CRAWL_PROC: Optional[subprocess.Popen] = None
_CRAWL_LOGS: deque[str] = deque(maxlen=1000)
_CRAWL_PUMP_TASK: Optional[asyncio.Task] = None

def _auth(creds: HTTPBasicCredentials = Depends(basic)) -> str:
    user_env = os.getenv("QTS_ADMIN_USER")
    pass_env = os.getenv("QTS_ADMIN_PASS")
    if not user_env or not pass_env:
        raise HTTPException(status_code=500, detail="Dashboard admin creds not configured")
    ok = compare_digest(creds.username or "", user_env) and compare_digest(creds.password or "", pass_env)
    if not ok:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized",
                            headers={"WWW-Authenticate": "Basic"})
    return creds.username

def _mongo_ui_url() -> str:
    return os.getenv("DASHBOARD_MONGO_UI_URL", "http://localhost:8081")

def _log(line: str):
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    _CRAWL_LOGS.append(f"[{ts}] {line.rstrip()}")

async def _pump_proc_output(proc: subprocess.Popen):
    assert proc.stdout is not None
    for line in iter(proc.stdout.readline, ""):
        if not line:
            break
        _log(line)
    code = proc.wait()
    _log(f"Process exited with code {code}")

def _jobdir_path() -> Path:
    return Path(os.getcwd()) / "app" / ".job" / "books"

def _has_resume_state(jobdir: Path) -> bool:
    return jobdir.exists() and any(jobdir.iterdir())

@router.get("", response_class=HTMLResponse)
async def dashboard_home(request: Request, _user: str = Depends(_auth)):
    running = _CRAWL_PROC is not None and _CRAWL_PROC.poll() is None
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "mongo_ui": _mongo_ui_url(),
            "crawl_running": running,
        },
    )

@router.get("/docs", response_class=HTMLResponse)
async def dashboard_docs(request: Request, _user: str = Depends(_auth)):
    return templates.TemplateResponse("docs.html", {"request": request, "mongo_ui": _mongo_ui_url()})

@router.get("/logs", response_class=HTMLResponse)
async def dashboard_logs(request: Request, _user: str = Depends(_auth)):
    return templates.TemplateResponse("logs.html", {"request": request, "logs": "\n".join(_CRAWL_LOGS)})

@router.get("/logs.txt", response_class=PlainTextResponse)
async def dashboard_logs_txt(_user: str = Depends(_auth)):
    return PlainTextResponse("\n".join(_CRAWL_LOGS) + "\n")

def _spawn_crawl(env_overrides: dict[str, str]) -> None:
    global _CRAWL_PROC, _CRAWL_PUMP_TASK
    if _CRAWL_PROC and _CRAWL_PROC.poll() is None:
        return
    _CRAWL_LOGS.clear()

    env = os.environ.copy()
    env.update(env_overrides)

    _CRAWL_PROC = subprocess.Popen(
        ["python", "-m", "scripts.run_crawl"],
        cwd=os.path.join(os.getcwd()),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    loop = asyncio.get_running_loop()
    _CRAWL_PUMP_TASK = loop.create_task(_pump_proc_output(_CRAWL_PROC))

@router.post("/crawl/start", response_class=RedirectResponse, status_code=303)
async def crawl_start(_user: str = Depends(_auth)):
    # ALWAYS fresh crawl (no resume)
    _log("Starting fresh crawl…")
    _spawn_crawl({"QTS_SCRAPY_RESUME": "false"})
    return RedirectResponse("/dashboard/logs", status_code=303)

@router.post("/crawl/start-resume", response_class=RedirectResponse, status_code=303)
async def crawl_start_resume(_user: str = Depends(_auth)):
    # Resume if there is state; otherwise fall back to fresh
    jobdir = _jobdir_path()
    if _has_resume_state(jobdir):
        _log(f"Starting crawl with resume (JOBDIR={jobdir})…")
        _spawn_crawl({"QTS_SCRAPY_RESUME": "true"})
    else:
        _log("No resume state found. Starting fresh crawl…")
        _spawn_crawl({"QTS_SCRAPY_RESUME": "false"})
    return RedirectResponse("/dashboard/logs", status_code=303)

@router.post("/crawl/stop", response_class=RedirectResponse, status_code=303)
async def crawl_stop(_user: str = Depends(_auth)):
    global _CRAWL_PROC, _CRAWL_PUMP_TASK
    if _CRAWL_PROC and _CRAWL_PROC.poll() is None:
        _log("Stopping crawl…")
        _CRAWL_PROC.terminate()
        try:
            _CRAWL_PROC.wait(timeout=5)
        except Exception:
            _CRAWL_PROC.kill()
    _CRAWL_PROC = None
    if _CRAWL_PUMP_TASK:
        _CRAWL_PUMP_TASK.cancel()
        _CRAWL_PUMP_TASK = None
    return RedirectResponse("/dashboard/logs", status_code=303)

@router.post("/schedule/run-now", response_class=RedirectResponse, status_code=303)
async def schedule_run_now(_user: str = Depends(_auth)):
    async def _run():
        import importlib.util, sys
        mod_path = os.path.join(os.getcwd(), "scripts", "schedule_daily.py")
        spec = importlib.util.spec_from_file_location("schedule_daily", mod_path)
        mod = importlib.util.module_from_spec(spec)  # type: ignore
        sys.modules["schedule_daily"] = mod
        assert spec and spec.loader
        spec.loader.exec_module(mod)  # type: ignore
        _log("Running scheduled job now…")
        await asyncio.to_thread(mod.run_crawl_blocking)  # scheduler's fresh crawl path
        _log("Crawl finished. Generating report…")
        await asyncio.to_thread(mod.build_daily_report_blocking)
        _log("Report generation done.")
    asyncio.create_task(_run())
    return RedirectResponse("/dashboard/logs", status_code=303)

@router.get("/logout")
def logout():
    return Response(status_code=401, headers={"WWW-Authenticate": "Basic"})

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_books import router as books_router
from app.api.routes_changes import router as changes_router
from app.api.routes_reports import router as reports_router
from app.api.routes_dashboard import router as dashboard_router

app = FastAPI(
    title="QTS Book API",
    version="1.0.0",
    description="Scraped books + changes with filters, pagination, and reports.",
)

# Optional CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

app.include_router(books_router)
app.include_router(changes_router)
app.include_router(reports_router)
app.include_router(dashboard_router)

@app.get("/", tags=["health"])
async def health():
    return {"status": "ok"}

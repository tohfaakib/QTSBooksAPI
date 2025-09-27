from fastapi import FastAPI
from app.api.routes_books import router as books_router
from app.api.routes_changes import router as changes_router

app = FastAPI(
    title="QTS Book API",
    version="1.0.0",
)

app.include_router(books_router)
app.include_router(changes_router)

@app.get("/", tags=["health"])
async def health():
    return {"status": "ok"}

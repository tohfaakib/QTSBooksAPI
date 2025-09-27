from fastapi import APIRouter, Query, Depends, HTTPException
from typing import Optional, Literal
from bson import ObjectId
from app.db.mongo import get_db
from app.models.book import Book
from app.api.deps import require_api_key

router = APIRouter(prefix="/books", tags=["books"], dependencies=[Depends(require_api_key)])

SortField = Literal["price", "rating", "reviews", "name", "crawled_at"]
SortOrder = Literal["asc", "desc"]

@router.get("", summary="List books with filters & sorting", description="Filter by category/price/rating, search by name, sort, and paginate.")
async def list_books(
    category: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None, description="price_incl_tax >= min_price"),
    max_price: Optional[float] = Query(None, description="price_incl_tax <= max_price"),
    min_rating: Optional[int] = Query(None, ge=0, le=5),
    q: Optional[str] = Query(None, description="name substring (case-insensitive)"),
    sort_by: SortField = "crawled_at",
    order: SortOrder = "desc",
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    db = get_db()
    query: dict = {}
    if category:
        query["category"] = category
    if min_rating is not None:
        query["rating"] = {"$gte": min_rating}

    price_cond = {}
    if min_price is not None:
        price_cond["$gte"] = min_price
    if max_price is not None:
        price_cond["$lte"] = max_price
    if price_cond:
        query["price_incl_tax_num"] = price_cond
    if q:
        query["name"] = {"$regex": q, "$options": "i"}

    sort_map = {
        "price": ("price_incl_tax_num", -1 if order == "desc" else 1),
        "rating": ("rating", -1 if order == "desc" else 1),
        "reviews": ("num_reviews", -1 if order == "desc" else 1),
        "name": ("name", 1 if order == "asc" else -1),
        "crawled_at": ("crawled_at", -1 if order == "desc" else 1),
    }
    sort_field, sort_dir = sort_map[sort_by]

    total = await db["books"].count_documents(query)
    cursor = db["books"].find(query).sort(sort_field, sort_dir).skip(skip).limit(limit)
    docs = [doc async for doc in cursor]
    for d in docs:
        d["_id"] = str(d["_id"])
    items = [Book(**d).model_dump(by_alias=True) for d in docs]

    return {"total": total, "skip": skip, "limit": limit, "items": items}

@router.get("/{book_id}", response_model=Book, summary="Get a book by id")
async def get_book(book_id: str):
    db = get_db()
    try:
        oid = ObjectId(book_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid book id")
    doc = await db["books"].find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    doc["_id"] = str(doc["_id"])
    return Book(**doc)

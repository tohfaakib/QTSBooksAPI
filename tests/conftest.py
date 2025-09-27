# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from bson import ObjectId
from datetime import datetime, timezone, timedelta

from app.api.main import app
import app.db.mongo as mongo_mod

# ---------- tiny in-memory Mongo-like fake ----------

def _match(doc, filt: dict) -> bool:
    for k, v in (filt or {}).items():
        if k == "changed_at":
            since = v.get("$gte")
            until = v.get("$lte")
            d = doc.get("changed_at")
            if since and (d is None or d < since):
                return False
            if until and (d is None or d > until):
                return False
            continue
        if isinstance(v, dict):
            if "$gte" in v or "$lte" in v:
                x = doc.get(k)
                if "$gte" in v and (x is None or x < v["$gte"]):
                    return False
                if "$lte" in v and (x is None or x > v["$lte"]):
                    return False
            elif "$regex" in v:
                import re
                flags = re.I if v.get("$options") == "i" else 0
                if not re.search(v["$regex"], doc.get(k, ""), flags):
                    return False
            else:
                if doc.get(k) != v:
                    return False
        else:
            if doc.get(k) != v:
                return False
    return True

class FakeCursor:
    def __init__(self, data):
        self.data = list(data)
    def sort(self, field, direction):
        reverse = direction == -1
        self.data.sort(key=lambda d: d.get(field), reverse=reverse)
        return self
    def skip(self, n):
        self.data = self.data[n:]
        return self
    def limit(self, n):
        self.data = self.data[:n]
        return self
    def __aiter__(self):
        async def gen():
            for d in self.data:
                yield d
        return gen()

class FakeCollection:
    def __init__(self, docs):
        self._docs = docs
    async def count_documents(self, filt):
        return sum(1 for d in self._docs if _match(d, filt or {}))
    def find(self, filt=None):
        return FakeCursor(d for d in self._docs if _match(d, (filt or {})))
    async def find_one(self, filt, projection=None):
        for d in self._docs:
            ok = True
            for k, v in (filt or {}).items():
                ok = ok and (d.get(k) == v)
            if ok:
                if projection:
                    nd = {k: d.get(k) for k, inc in projection.items() if inc == 1}
                    nd["_id"] = d["_id"]
                    return nd
                return d
        return None
    def aggregate(self, pipeline):
        stage1, stage2 = pipeline
        group_key = stage1["$group"]["_id"][1:]  # "$category" -> "category"
        counts = {}
        for d in self._docs:
            k = d.get(group_key)
            counts[k] = counts.get(k, 0) + 1
        rows = [{"_id": k, "count": v} for k, v in counts.items()]
        rows.sort(key=lambda r: r["_id"])
        class _Agg:
            async def __aiter__(self_non):
                for r in rows:
                    yield r
        return _Agg()

class FakeDB(dict):
    pass

@pytest.fixture()
def client(monkeypatch):
    # seed docs
    now = datetime.now(timezone.utc)
    books = [
        {
            "_id": ObjectId(),
            "url": "https://example.com/a",
            "name": "Alpha Book",
            "description": "A great start",
            "category": "Travel",
            "image_url": "https://example.com/a.jpg",
            "rating": 4,
            "availability": "In stock",
            "price_incl_tax": "£12.00",
            "price_excl_tax": "£10.00",
            "price_incl_tax_num": 12.0,
            "price_excl_tax_num": 10.0,
            "tax": "£2.00",
            "num_reviews": 5,
            "crawled_at": now - timedelta(hours=3),
            "source": "test",
            "content_hash": "h1",
        },
        {
            "_id": ObjectId(),
            "url": "https://example.com/b",
            "name": "Bravo Stories",
            "description": "Second",
            "category": "Fiction",
            "image_url": "https://example.com/b.jpg",
            "rating": 5,
            "availability": "In stock",
            "price_incl_tax": "£25.00",
            "price_excl_tax": "£20.00",
            "price_incl_tax_num": 25.0,
            "price_excl_tax_num": 20.0,
            "tax": "£5.00",
            "num_reviews": 12,
            "crawled_at": now - timedelta(hours=1),
            "source": "test",
            "content_hash": "h2",
        },
    ]
    changes = [
        {
            "_id": ObjectId(),
            "url": "https://example.com/a",
            "changed_at": now - timedelta(hours=2),
            "change_kind": "new",
            "significant": True,
            "fields_changed": {"price_incl_tax": {"prev": "£0.00", "new": "£12.00"}},
            "price_delta": 12.0,
            "prev_hash": None,
            "new_hash": "h1",
        },
        {
            "_id": ObjectId(),
            "url": "https://example.com/b",
            "changed_at": now - timedelta(minutes=30),
            "change_kind": "update",
            "significant": False,
            "fields_changed": {"availability": {"prev": "In stock", "new": "Out of stock"}},
            "price_delta": 0.0,
            "prev_hash": "h_old",
            "new_hash": "h2",
        },
    ]

    fdb = FakeDB()
    fdb["books"] = FakeCollection(books)
    fdb["changes"] = FakeCollection(changes)

    def _fake_get_db():
        return fdb

    # patch the module and any routers that imported the symbol
    monkeypatch.setattr(mongo_mod, "get_db", _fake_get_db, raising=False)

    import app.api.routes_books as routes_books
    import app.api.routes_changes as routes_changes
    monkeypatch.setattr(routes_books, "get_db", _fake_get_db, raising=False)
    monkeypatch.setattr(routes_changes, "get_db", _fake_get_db, raising=False)

    # optional routers: patch only if present
    try:
        import app.api.routes_books_categories as routes_books_categories  # type: ignore
        monkeypatch.setattr(routes_books_categories, "get_db", _fake_get_db, raising=False)
    except ImportError:
        pass
    try:
        import app.api.routes_reports as routes_reports  # type: ignore
        monkeypatch.setattr(routes_reports, "get_db", _fake_get_db, raising=False)
    except ImportError:
        pass

    from app.api.deps import require_api_key
    app.dependency_overrides[require_api_key] = lambda: None

    return TestClient(app)

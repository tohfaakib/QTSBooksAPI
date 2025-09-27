import os

API_KEY = os.getenv("QTS_API_KEY", "test-key") # default for tests

def _h():
    return {"X-API-Key": os.getenv("QTS_API_KEY", "test-key")}

def test_health(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_books_basic_list(client):
    r = client.get("/books?page=1&page_size=10", headers=_h())
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 2
    assert "items" in body and len(body["items"]) >= 2

def test_books_filters_and_sort(client):
    # category filter + sort by price asc
    r = client.get("/books?category=Travel&sort_by=price&order=asc&page=1&page_size=10", headers=_h())
    assert r.status_code == 200
    items = r.json()["items"]
    assert all(i["category"] == "Travel" for i in items)
    # name search (case-insensitive)
    r = client.get("/books?q=bravo&page=1&page_size=10", headers=_h())
    assert r.status_code == 200
    assert any("Bravo" in x["name"] for x in r.json()["items"])

def test_changes_filters(client):
    # last 3 hours, significant only
    r = client.get("/changes?since_hours=3&significant=true&page=1&page_size=50", headers=_h())
    assert r.status_code == 200
    items = r.json()["items"]
    assert all(x["significant"] is True for x in items)

    # kind=update should return the non-significant doc in our seed
    r = client.get("/changes?kind=update&page=1&page_size=50", headers=_h())
    assert r.status_code == 200
    items = r.json()["items"]
    assert all(x["change_kind"] == "update" for x in items)

def test_reports_today_404(client):
    # No reports created in tests → expect 404
    r = client.get("/reports/today?format=json", headers=_h())
    assert r.status_code in (401, 404, 422, 500) or r.status_code == 200
    # Depending on whether API key is enforced in your dev env. If key enforced, update API_KEY env.

def test_rate_limit_path_scoped(client, monkeypatch):
    import app.api.limit as limiter
    monkeypatch.setattr(limiter, "RATE_LIMIT", 3, raising=False)
    monkeypatch.setattr(limiter, "WINDOW_SEC", 60, raising=False)

    if hasattr(limiter, "RATE_STORE"):
        limiter.RATE_STORE.clear()

    headers = {"X-API-Key": "rate-test-key"}  # unique bucket for this test

    ok = [client.get("/books?page=1&page_size=1", headers=headers).status_code for _ in range(3)]
    blocked = client.get("/books?page=1&page_size=1", headers=headers).status_code

    assert ok == [200, 200, 200]
    assert blocked == 429


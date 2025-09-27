from fastapi.testclient import TestClient
from app.api.main import app
from app.api.deps import require_api_key
import os

def test_api_key_required(monkeypatch):
    if require_api_key in app.dependency_overrides:
        del app.dependency_overrides[require_api_key]

    client = TestClient(app)

    # no key -> 401 or 403 (your app uses 403)
    r = client.get("/books?page=1&page_size=1")
    assert r.status_code in (401, 403)

    # right key -> 200
    key = os.getenv("QTS_API_KEY", "test-key")
    r = client.get("/books?page=1&page_size=1", headers={"X-API-Key": key})
    assert r.status_code == 200

    # restore override for other tests if you use it elsewhere
    app.dependency_overrides[require_api_key] = lambda: None

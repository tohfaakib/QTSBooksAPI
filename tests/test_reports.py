from fastapi.testclient import TestClient
from app.api.main import app
from app.api.deps import require_api_key

def test_reports_basic(monkeypatch):
    # bypass API key for this test (if you’re doing that pattern)
    app.dependency_overrides[require_api_key] = lambda: None
    client = TestClient(app)

    r = client.get("/reports/list")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, dict)
    assert "files" in data
    assert isinstance(data["files"], list)

    r = client.get("/reports/today?format=json")
    assert r.status_code in (404, 200)  # 404 if no report for today

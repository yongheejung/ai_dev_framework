from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_ping_without_tenant():
    response = client.get("/api/v1/ping")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"] == "pong"


def test_ping_with_tenant():
    response = client.get("/api/v1/ping", headers={"X-Tenant-Id": "demo"})
    assert response.status_code == 200
    assert response.json()["data"] == "pong (tenant=demo)"

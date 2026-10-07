import pytest

from app import create_app

TOKEN = "unit-test-token"
AUTH = {"X-API-Token": TOKEN}


@pytest.fixture()
def client(tmp_path):
    app = create_app({"DATA_DIR": str(tmp_path), "API_TOKEN": TOKEN, "APP_VERSION": "1.2.3", "APP_ENV": "test", "TESTING": True})
    return app.test_client()


def test_health_and_ready(client):
    assert client.get("/health").get_json() == {"status": "healthy"}
    assert client.get("/ready").get_json() == {"status": "ready"}


def test_info_reflects_configuration(client):
    data = client.get("/api/info").get_json()
    assert data["version"] == "1.2.3" and data["environment"] == "test"


def test_index_page(client):
    html = client.get("/").get_data(as_text=True)
    assert "DevOps Task Tracker" in html and "1.2.3" in html


def test_create_requires_token(client):
    assert client.post("/api/tasks", json={"title": "x"}).status_code == 401
    assert client.post("/api/tasks", json={"title": "x"}, headers={"X-API-Token": "wrong"}).status_code == 401


def test_writes_disabled_without_configured_token(tmp_path):
    app = create_app({"DATA_DIR": str(tmp_path), "API_TOKEN": ""})
    assert app.test_client().post("/api/tasks", json={"title": "x"}, headers=AUTH).status_code == 503


def test_task_crud_lifecycle(client):
    created = client.post("/api/tasks", json={"title": "write docs"}, headers=AUTH)
    assert created.status_code == 201
    tid = created.get_json()["id"]
    assert client.get("/api/tasks").get_json()[0]["title"] == "write docs"
    upd = client.put(f"/api/tasks/{tid}", json={"done": True}, headers=AUTH)
    assert upd.get_json()["done"] is True
    assert client.delete(f"/api/tasks/{tid}", headers=AUTH).status_code == 204
    assert client.get("/api/tasks").get_json() == []


def test_validation_and_not_found(client):
    assert client.post("/api/tasks", json={"title": "  "}, headers=AUTH).status_code == 400
    assert client.put("/api/tasks/999", json={"done": True}, headers=AUTH).status_code == 404
    assert client.delete("/api/tasks/999", headers=AUTH).status_code == 404
    assert client.get("/nope").status_code == 404


def test_metrics_endpoint(client):
    client.get("/health")
    body = client.get("/metrics").get_data(as_text=True)
    assert "http_requests_total" in body and "tasks_total" in body and "app_info" in body

import os
import tempfile

os.environ["DATA_DIR"] = tempfile.mkdtemp()

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def test_health():
    assert client.get("/api/health").json() == {"status": "ok"}


def test_kris_seeded_and_status_change():
    kris = client.get("/api/kris").json()
    assert len(kris) == 7
    r = client.patch("/api/kris/OI-02/status", json={"status": "paused"})
    assert r.json()["status"] == "paused"
    client.patch("/api/kris/OI-02/status", json={"status": "active"})


def test_run_creates_exceptions():
    before = len(client.get("/api/exceptions").json())
    r = client.post("/api/runs", json={"kriId": "OI-02", "period": "P8 · Aug 2026"})
    assert r.status_code == 201
    body = r.json()
    assert body["run"]["kriId"] == "OI-02"
    assert len(body["exceptions"]) >= 1
    assert len(client.get("/api/exceptions").json()) == before + len(body["exceptions"])


def test_exception_to_planner_and_draft():
    exc = client.get("/api/exceptions").json()[0]
    item = client.post(f"/api/exceptions/{exc['id']}/planner").json()
    assert item["status"] == "New"
    drafted = client.post(f"/api/planner/{item['id']}/draft", json={"policy": "v3.2"}).json()
    assert drafted["status"] == "Plan drafted" and len(drafted["plan"]) == 8
    live = client.patch(f"/api/planner/{item['id']}", json={"status": "Live"}).json()
    assert live["status"] == "Live"


def test_reset():
    assert client.post("/api/settings/reset").status_code == 204
    assert len(client.get("/api/planner").json()) == 3

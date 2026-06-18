import pytest
from fastapi.testclient import TestClient
from app.main import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


def test_create_bin(client):
    b = client.post("/api/bins").json()["bin_id"]
    assert isinstance(b, str) and len(b) >= 6


def test_capture_post_with_body_and_query(client):
    b = client.post("/api/bins").json()["bin_id"]
    r = client.post(f"/b/{b}/webhook?source=stripe",
                    json={"event": "charge.succeeded"},
                    headers={"X-Signature": "abc"})
    assert r.status_code == 200 and r.json()["received"] is True

    reqs = client.get(f"/api/bins/{b}/requests").json()
    assert len(reqs) == 1
    captured = reqs[0]
    assert captured["method"] == "POST"
    assert captured["path"] == "/webhook"
    assert captured["query"] == {"source": "stripe"}
    assert "charge.succeeded" in captured["body"]
    assert captured["headers"]["x-signature"] == "abc"


def test_multiple_methods_captured(client):
    b = client.post("/api/bins").json()["bin_id"]
    client.get(f"/b/{b}/a")
    client.put(f"/b/{b}/b", content="x")
    client.delete(f"/b/{b}/c")
    methods = [r["method"] for r in client.get(f"/api/bins/{b}/requests").json()]
    assert methods == ["GET", "PUT", "DELETE"]


def test_since_polling(client):
    b = client.post("/api/bins").json()["bin_id"]
    client.get(f"/b/{b}/1")
    client.get(f"/b/{b}/2")
    newer = client.get(f"/api/bins/{b}/requests?since=1").json()
    assert [r["id"] for r in newer] == [2]


def test_clear_and_unknown(client):
    b = client.post("/api/bins").json()["bin_id"]
    client.get(f"/b/{b}/x")
    assert client.delete(f"/api/bins/{b}/requests").json()["ok"] is True
    assert client.get(f"/api/bins/{b}/requests").json() == []
    assert client.get("/api/bins/doesnotexist/requests").status_code == 404
    assert client.post("/b/doesnotexist/x").status_code == 404


def test_configured_response_is_returned(client):
    b = client.post("/api/bins").json()["bin_id"]
    client.put(f"/api/bins/{b}/response",
               json={"status": 503, "body": "down for maintenance", "content_type": "text/plain"})
    r = client.post(f"/b/{b}/hook", follow_redirects=False)
    assert r.status_code == 503 and r.text == "down for maintenance"
    assert r.headers["content-type"].startswith("text/plain")
    # the request is still captured even though a custom response was returned
    assert len(client.get(f"/api/bins/{b}/requests").json()) == 1
    # reset -> back to the default acknowledgement
    client.delete(f"/api/bins/{b}/response")
    assert client.post(f"/b/{b}/hook").json()["received"] is True


def test_get_response_defaults(client):
    b = client.post("/api/bins").json()["bin_id"]
    cfg = client.get(f"/api/bins/{b}/response").json()
    assert cfg["custom"] is False and cfg["status"] == 200


def test_response_status_is_validated(client):
    b = client.post("/api/bins").json()["bin_id"]
    assert client.put(f"/api/bins/{b}/response", json={"status": 999}).status_code == 422


def test_large_body_is_truncated():
    from app.store import BinStore
    c = TestClient(create_app(BinStore(max_body=8)))
    b = c.post("/api/bins").json()["bin_id"]
    c.post(f"/b/{b}/x", content="0123456789ABCDEF")
    req = c.get(f"/api/bins/{b}/requests").json()[0]
    assert req["truncated"] is True and len(req["body"]) == 8

import hmac
import hashlib
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def sign(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

def seed_messages(client: TestClient, secret: str, msgs):
    for m in msgs:
        raw = client._encode_json(m, "application/json")
        sig = sign(secret, raw)
        client.post("/webhook", data=raw, headers={"Content-Type": "application/json", "X-Signature": sig})

def test_pagination_and_filters(monkeypatch):
    monkeypatch.setenv("WEBHOOK_SECRET", "testsecret")
    monkeypatch.setenv("DATABASE_URL", "sqlite:////tmp/test_app_messages.db")
    local_client = TestClient(app)

    msgs = [
        {"message_id": "m1", "from": "+919876543210", "to": "+14155550100", "ts": "2025-01-15T09:00:00Z", "text": "Earlier"},
        {"message_id": "m2", "from": "+919876543210", "to": "+14155550100", "ts": "2025-01-15T09:30:00Z", "text": "Mid"},
        {"message_id": "m3", "from": "+911234567890", "to": "+14155550100", "ts": "2025-01-15T10:00:00Z", "text": "Hello"},
    ]
    seed_messages(local_client, "testsecret", msgs)

    r = local_client.get("/messages")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 3
    assert data["data"][0]["message_id"] == "m1"  # ts asc
    assert data["data"][1]["message_id"] == "m2"
    assert data["data"][2]["message_id"] == "m3"

    r2 = local_client.get("/messages?limit=2&offset=0")
    assert r2.status_code == 200
    assert len(r2.json()["data"]) == 2

    r3 = local_client.get("/messages?from=+919876543210")
    assert r3.status_code == 200
    assert r3.json()["total"] == 2

    r4 = local_client.get("/messages?since=2025-01-15T09:30:00Z")
    assert r4.status_code == 200
    assert r4.json()["total"] == 2

    r5 = local_client.get("/messages?q=Hello")
    assert r5.status_code == 200
    assert r5.json()["total"] == 1

import hmac
import hashlib
from fastapi.testclient import TestClient
from app.main import app

def sign(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

def seed_messages(client: TestClient, secret: str, msgs):
    for m in msgs:
        raw = client._encode_json(m, "application/json")
        sig = sign(secret, raw)
        client.post("/webhook", data=raw, headers={"Content-Type": "application/json", "X-Signature": sig})

def test_stats(monkeypatch):
    monkeypatch.setenv("WEBHOOK_SECRET", "testsecret")
    monkeypatch.setenv("DATABASE_URL", "sqlite:////tmp/test_app_stats.db")
    local_client = TestClient(app)

    msgs = [
        {"message_id": "m1", "from": "+919876543210", "to": "+14155550100", "ts": "2025-01-10T09:00:00Z", "text": "A"},
        {"message_id": "m2", "from": "+919876543210", "to": "+14155550100", "ts": "2025-01-15T10:00:00Z", "text": "B"},
        {"message_id": "m3", "from": "+911234567890", "to": "+14155550100", "ts": "2025-01-12T10:00:00Z", "text": "C"},
    ]
    seed_messages(local_client, "testsecret", msgs)

    r = local_client.get("/stats")
    assert r.status_code == 200
    s = r.json()
    assert s["total_messages"] == 3
    assert s["senders_count"] == 2
    assert s["first_message_ts"] == "2025-01-10T09:00:00Z"
    assert s["last_message_ts"] == "2025-01-15T10:00:00Z"
    # Sum of listed senders equals total_messages for those senders
    assert sum(x["count"] for x in s["messages_per_sender"]) == 3

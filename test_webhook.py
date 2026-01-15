import hmac
import hashlib
from fastapi.testclient import TestClient
from app.main import app
from app.config import load_settings

client = TestClient(app)

def sign(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

def test_invalid_signature():
    body = {
        "message_id": "m1",
        "from": "+919876543210",
        "to": "+14155550100",
        "ts": "2025-01-15T10:00:00Z",
        "text": "Hello",
    }
    r = client.post("/webhook", json=body, headers={"X-Signature": "123"})
    assert r.status_code == 401
    assert r.json()["detail"] == "invalid signature"

def test_valid_insert_and_duplicate(monkeypatch):
    # Ensure secret is set
    monkeypatch.setenv("WEBHOOK_SECRET", "testsecret")
    monkeypatch.setenv("DATABASE_URL", "sqlite:////tmp/test_app.db")

    # Trigger lifespan by creating a new client
    local_client = TestClient(app)

    body = {
        "message_id": "m1",
        "from": "+919876543210",
        "to": "+14155550100",
        "ts": "2025-01-15T10:00:00Z",
        "text": "Hello",
    }
    raw = local_client._encode_json(body, "application/json")
    sig = sign("testsecret", raw)

    r1 = local_client.post("/webhook", data=raw, headers={"Content-Type": "application/json", "X-Signature": sig})
    assert r1.status_code == 200
    assert r1.json() == {"status": "ok"}

    r2 = local_client.post("/webhook", data=raw, headers={"Content-Type": "application/json", "X-Signature": sig})
    assert r2.status_code == 200
    assert r2.json() == {"status": "ok"}

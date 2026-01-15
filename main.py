import hmac
import hashlib
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request, Header, HTTPException, Query
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware

from .config import load_settings, Settings
from .logging_utils import JSONLoggerMiddleware
from .metrics import (
    metrics_endpoint,
    http_requests_total,
    request_latency_ms,
    webhook_requests_total,
)
from .models import WebhookMessage, MessagesResponse, StatsResponse
from .storage import get_conn, init_schema, insert_message, list_messages, stats, ready


def verify_signature(secret: str, body: bytes, signature: str) -> bool:
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings: Settings = load_settings()
    if not settings.webhook_secret:
        # Fail readiness until secret is set
        app.state.settings = settings
        app.state.conn = None
        yield
        return

    conn = get_conn(settings.database_url)
    init_schema(conn)

    app.state.settings = settings
    app.state.conn = conn

    yield

    if conn:
        conn.close()


app = FastAPI(title="Lyftr AI Webhook API", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
# JSON logs + metrics
app.add_middleware(JSONLoggerMiddleware)


@app.get("/health/live")
def health_live():
    return {"status": "live"}


@app.get("/health/ready")
def health_ready(request: Request):
    settings: Settings = request.app.state.settings
    conn = getattr(request.app.state, "conn", None)
    if not settings.webhook_secret:
        raise HTTPException(status_code=503, detail="secret not set")
    if not conn or not ready(conn):
        raise HTTPException(status_code=503, detail="db not ready")
    return {"status": "ready"}


@app.post("/webhook")
async def webhook(request: Request, x_signature: Optional[str] = Header(None)):
    settings: Settings = request.app.state.settings
    conn = request.app.state.conn

    raw = await request.body()
    if not x_signature or not verify_signature(settings.webhook_secret, raw, x_signature):
        webhook_requests_total.labels(result="invalid_signature").inc()
        raise HTTPException(status_code=401, detail="invalid signature")

    # Validate payload (Pydantic v2)
    try:
        payload_in = WebhookMessage.model_validate_json(raw)
    except Exception:
        webhook_requests_total.labels(result="validation_error").inc()
        raise HTTPException(status_code=422, detail="validation error")

    payload = payload_in.model_dump()
    created, duplicate, err = insert_message(conn, payload)
    if err:
        webhook_requests_total.labels(result="error").inc()
        # Graceful handling, still 200 per spec
        return JSONResponse(status_code=200, content={"status": "ok"})

    webhook_requests_total.labels(result="created" if created else "duplicate").inc()
    # Attach webhook-specific fields for logging via request.state
    request.state.extra_log = {
        "message_id": payload.get("message_id"),
        "dup": duplicate,
        "result": "created" if created else "duplicate",
    }
    return {"status": "ok"}


@app.get("/messages", response_model=MessagesResponse)
def get_messages(
    request: Request,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    from_filter: Optional[str] = Query(None, alias="from"),
    since: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
):
    conn = request.app.state.conn
    data, total = list_messages(conn, limit=limit, offset=offset,
                                from_filter=from_filter, since=since, q=q)
    return {
        "data": data,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@app.get("/stats", response_model=StatsResponse)
def get_stats(request: Request):
    conn = request.app.state.conn
    return stats(conn)


@app.get("/metrics")
def metrics():
    # Return text exposition format
    return PlainTextResponse(metrics_endpoint())

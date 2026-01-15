import time
import json
import uuid
from datetime import datetime, timezone
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .metrics import http_requests_total, request_latency_ms


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class JSONLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())
        start = time.perf_counter()

        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            # Ensure we still log an error line
            response = Response(status_code=500, content=b'{"detail":"internal error"}', media_type="application/json")

        latency_ms = int((time.perf_counter() - start) * 1000)

        # Metrics: http_requests_total and latency
        path = request.url.path
        status = response.status_code
        http_requests_total.labels(path=path, status=str(status)).inc()
        request_latency_ms.observe(latency_ms)

        # Base log
        log = {
            "ts": iso_now(),
            "level": "INFO" if status < 400 else "ERROR",
            "request_id": request_id,
            "method": request.method,
            "path": path,
            "status": status,
            "latency_ms": latency_ms,
        }

        # Webhook extras (if set by route)
        extra = getattr(request.state, "extra_log", None)
        if extra and path == "/webhook":
            log.update({
                "message_id": extra.get("message_id"),
                "dup": bool(extra.get("dup")),
                "result": extra.get("result"),
            })

        print(json.dumps(log, ensure_ascii=False))
        return response

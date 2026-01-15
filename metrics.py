from prometheus_client import Counter, Histogram, generate_latest

# HTTP requests counter with labels path and status
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["path", "status"],
)

# Webhook processing outcomes
webhook_requests_total = Counter(
    "webhook_requests_total",
    "Webhook processing outcomes",
    ["result"],  # created, duplicate, invalid_signature, validation_error, error
)

# Simple latency histogram (ms)
request_latency_ms = Histogram(
    "request_latency_ms",
    "Request latency in milliseconds",
    buckets=(50, 100, 200, 500, 1000, float("inf")),
)

def metrics_endpoint() -> str:
    return generate_latest().decode("utf-8")

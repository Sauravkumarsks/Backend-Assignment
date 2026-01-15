Setup Used - VS code + Copilot + occasional ChatGPT prompts

# Lyftr AI — Backend Assignment

Production-style FastAPI service for ingesting WhatsApp-like messages exactly once, with HMAC signature validation, health probes, pagination, stats, Prometheus metrics, and structured JSON logs.

## How to run

### Prerequisites
- Docker & Docker Compose
- GNU Make (optional)
- Environment variables:
```bash
export WEBHOOK_SECRET="testsecret"
export DATABASE_URL="sqlite:////data/app.db"
export LOG_LEVEL="INFO"

# Launchpad FDE — Enterprise AI Deployment Accelerator

An FDE-style reference implementation for taking a configurable AI workflow from candidate to production: evaluation gates, canary routing, rollback, idempotency and operational telemetry.

## What it demonstrates

- Per-use-case **release configuration**: prompt, model, status and traffic allocation.
- An **evaluation gate** that blocks promotion below a configured quality threshold.
- Deterministic **canary routing**: the same tenant/request key consistently lands on the same release bucket.
- Explicit **rollback** to remove a release from traffic.
- Idempotency keys for safe request retries.
- Request-level telemetry with trace IDs, p50/p95 latency, error rate and estimated spend.
- FastAPI, Docker, tests and CI.

## Run locally

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py --serve
# http://127.0.0.1:8005/docs
pytest -q
```

Use Docker with `docker compose up --build`.

## Example release lifecycle

1. A candidate is registered with its prompt/model configuration.
2. Golden evaluation cases run before promotion.
3. A passing candidate is activated at a small canary percentage.
4. Runtime metrics determine whether it is expanded or rolled back.

## Production extensions

Persist configurations and idempotency keys in a durable store; enforce tenant authorization; connect real provider adapters with timeout, retry/backoff and circuit breakers; add OpenTelemetry; use real eval datasets with calibrated LLM-as-a-judge; and integrate deployment state with CI/CD.

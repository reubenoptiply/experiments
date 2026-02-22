# Demo Account Simulator (Shop 1380)

Digital-twin demo environment for Optiply Shop 1380 (Cosmetics): 365 days of synthetic inventory/sales/PO history and a daily maintainer that keeps the dashboard "live".

## Two ways to run

| Approach | Where | Use case |
|----------|------|----------|
| **Python engine (Cloud Run)** | [python-approach/](python-approach/) | Service that exposes `POST /simulate` and `POST /maintain`; Retool calls the API and posts payloads to Optiply. |
| **Pure Retool Workflows** | [plan/](plan/) | Creator + Maintainer built entirely in Retool (no Python service). Simulation runs in a Retool Python block; SQL blocks handle stocks and date shifts. |

- **Spec & API:** [docs/CONTEXT.md](docs/CONTEXT.md) — technical specification, API contract, implementation status.
- **Retool-only build:** [plan/README.md](plan/README.md) — brief, tech plan, T1–T4 tickets, Builder Guide, paste-ready simulation script. To execute quickly: [plan/EXECUTION_RUNBOOK.md](plan/EXECUTION_RUNBOOK.md).
- **Gemini CLI:** [docs/GEMINI.md](docs/GEMINI.md).

---

## Setup (Python engine)

1. **Environment**
   - In `python-approach/`, copy `.env.example` to `.env` and set `DATABASE_URL` (PostgreSQL connection string).
   - Optional: set `FAIL_FAST_NO_DB=1` in production (e.g. Cloud Run) so the app fails at startup if `DATABASE_URL` is missing.

2. **Install**
   ```bash
   cd python-approach && pip install -r requirements.txt
   ```

3. **Run**
   - Local: from `python-approach/`, run `uvicorn src.main:app --host 0.0.0.0 --port 8080` (or port 8000 if you prefer).
   - Docker: build from `python-approach/`; port 8080 (see `python-approach/Dockerfile`).

## Endpoints

- `GET /` – Liveness
- `GET /health` – DB health (503 if DB not set or unreachable)
- `POST /simulate` – Phase A: full reset, 365-day simulation (body: `webshop_id`, `products` with `supplier_id`; only whitelisted product IDs are used)
- `POST /maintain?webshop_id=1380` – Phase B: shift dates forward to today

## Tests

From the `demo-account-simulator/python-approach` directory (or with `PYTHONPATH=python-approach` from `demo-account-simulator`):

```bash
cd python-approach && pytest tests/ -v
```

## Deploy to Google Cloud Run

See [docs/DEPLOY-CLOUDRUN.md](docs/DEPLOY-CLOUDRUN.md) for steps: enable APIs, create Artifact Registry repo, build from `python-approach/`, push and deploy with `gcloud run deploy` and `DATABASE_URL` (and optionally `FAIL_FAST_NO_DB=1`). Use the resulting service URL in Retool (see [docs/RETOOL.md](docs/RETOOL.md)).

## Retool (Python engine path)

When using the Python service, the simulation engine returns `api_payloads` (sales, buy_orders). Post these to the Optiply Public API in batches with a short delay (e.g. 100–200 ms between requests) to respect rate limits. For the **pure Retool** path (no Python service), use the [plan/](plan/) folder instead.

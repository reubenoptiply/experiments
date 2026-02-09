# Demo Account Simulator (Shop 1380)

Digital-twin demo environment for Optiply Shop 1380 (Cosmetics): a Python engine that generates 365 days of synthetic inventory/sales/PO history and a daily "maintainer" that shifts dates forward.

See [docs/CONTEXT.md](docs/CONTEXT.md) for the full technical specification. Gemini CLI context: [docs/GEMINI.md](docs/GEMINI.md).

## Setup

1. **Environment**
   - Copy `.env.example` to `.env` and set `DATABASE_URL` (PostgreSQL connection string).
   - Optional: set `FAIL_FAST_NO_DB=1` in production (e.g. Cloud Run) so the app fails at startup if `DATABASE_URL` is missing.

2. **Install**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run**
   - Local: `uvicorn src.main:app --host 0.0.0.0 --port 8080` (or port 8000 if you prefer).
   - Docker: port 8080 (see `Dockerfile`).

## Endpoints

- `GET /` – Liveness
- `GET /health` – DB health (503 if DB not set or unreachable)
- `POST /simulate` – Phase A: full reset, 365-day simulation (body: `webshop_id`, `products` with `supplier_id`; only whitelisted product IDs are used)
- `POST /maintain?webshop_id=1380` – Phase B: shift dates forward to today

## Tests

From the `demo-account-simulator` directory (or repo root with `PYTHONPATH` set):

```bash
pytest tests/ -v
```

## Deploy to Google Cloud Run

See [docs/DEPLOY-CLOUDRUN.md](docs/DEPLOY-CLOUDRUN.md) for steps: enable APIs, create Artifact Registry repo, build and push the image, deploy with `gcloud run deploy` and `DATABASE_URL` (and optionally `FAIL_FAST_NO_DB=1`). Use the resulting service URL in Retool (see [docs/RETOOL.md](docs/RETOOL.md)).

## Retool

The simulation engine returns `api_payloads` (sales, buy_orders). Post these to the Optiply Public API in batches with a short delay (e.g. 100–200 ms between requests) to respect rate limits.

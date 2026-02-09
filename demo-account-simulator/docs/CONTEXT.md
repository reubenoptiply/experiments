# Technical Specification: Shop 1380 Inventory Simulation Engine

**Convention:** Whenever you make an update or change to the project, update this file (`docs/CONTEXT.md`) so we know what's going on. In particular, keep **§8 Implementation status** and any affected sections (API, workflows, docs) in sync with the code and other docs.

---

## 1. Project Mission
Create a "Digital Twin" demo environment for Optiply Shop `1380` (Cosmetics). 
- **The Creator**: Python engine to generate 365 days of synthetic history.
- **The Maintainer**: Daily automation to shift dates forward, ensuring the dashboard is always "live".

## 2. Tech Stack & Integration
| Component | Technology | Responsibility |
| :--- | :--- | :--- |
| **Database** | PostgreSQL | Source of truth for all tables. |
| **Logic Engine** | Python (FastAPI/Cloud Run) | Simulation math and data generation. |
| **Orchestration** | Retool Workflows | Triggers, API loops, and manual overrides. |
| **API Boundary** | Optiply Public API | Used for creating `buy_orders` and `sell_orders`. |
| **SQL Boundary** | Direct PG Connection | Used for high-volume `stocks` history inserts. |

## 3. Product Archetypes (The Demand Engine)
Simulation logic must parse keywords in `webshop_products.name` (e.g., "Product Name (Seasonal Summer)").

| Archetype | Mathematical Shape / Logic |
| :--- | :--- |
| **Stable (Fast/Slow)** | Constant mean with ±15% random noise. |
| **Seasonal (Summer/Winter)**| Gaussian peak: $qty = base + (base \times 3 \cdot e^{-(day-peak)^2 / (2 \cdot width^2)})$. |
| **Trend (Pos/Neg)** | Linear growth/decay (1x to 3x or 100% to 20%) in the final 120 days. |
| **Stockout Prone** | **Demand-side**: 2x normal demand. **Supply-side**: ROP is cut to 80% of lead time demand. |
| **New Launch** | Zero sales until Day -30, then 2.5x spike (Success) or 0.5x (Flop). |
| **Outlier Spikes** | 3% chance daily for an 8x demand multiplier (Influencer effect). |
| **Lumpy/Sporadic** | **Lumpy**: 3% chance for bulk (qty 50-200). **Sporadic**: 8% chance for qty 3. |
| **Obsolete** | Hard cut-off: 0 demand in the final 60 days. |

## 4. Operational Workflows

### Phase A: The Creator (Full Reset)
1. **Targeting**: Only modify records where `webshop_id = 1380` and `product_id` is in the authorized demo list.
2. **Cleanup**: Execute `UPDATE stocks SET deleted_at = NOW() WHERE webshop_id = 1380`.
3. **Simulation**:
   - Back-calculate stock starting at `current_stock + 800`.
   - Run daily loop (365 days) calculating **Inbound** (PO receipts) -> **Outbound** (Sales) -> **Reorder** (ROP check).
4. **Data Injection**:
   - **Sales/POs**: Convert to JSON payloads for Public API `POST` endpoints.
   - **Stocks**: Batch insert (2000 rows/batch) via SQL with `ON CONFLICT (product_id, date) DO UPDATE`.

### Phase B: The Maintainer (Daily Shift)
Run nightly to keep data fresh:
```sql
WITH lag AS (SELECT (CURRENT_DATE - MAX(date)::date) as days FROM stocks WHERE webshop_id=1380)
UPDATE sell_orders SET placed = placed + (SELECT days FROM lag) * INTERVAL '1 day' WHERE webshop_id=1380;
UPDATE buy_orders SET placed = placed + (SELECT days FROM lag) * INTERVAL '1 day', expected_delivery_date = ...;
UPDATE stocks SET date = date + (SELECT days FROM lag) * INTERVAL '1 day' WHERE webshop_id=1380;
```

## 5. Constraints & Safety
- **Product ID White-list**: `28666283, 28666286, 28666287, 28666288, 28666289, 28666290, 28666291, 28666292, 28666293, 28666294, 28666295, 28666296, 28666297, 28666298, 28666299, 28666300, 28666301, 28666302, 28666303, 28666304, 28666305, 28666306, 28666307, 28666308, 28666309, 28666310, 28666311, 28666312, 28666313, 28666314, 28666315, 28666316`.
- **Concurrency**: Simulation must handle potential API rate limits (batching/delays).
- **Date Format**: Standardize on ISO8601 (`YYYY-MM-DDTHH:MM:SSZ`) for API and `YYYY-MM-DD` for SQL.

## 6. API Contract (Simulation Engine)

**Base URL**: Service URL (e.g. Cloud Run or local).

- **`GET /`** – Liveness; returns `{"status": "active", "shop": 1380}`.
- **`GET /health`** – Health check; returns 200 with `{"status": "healthy"}` or 503 if DB not configured or unreachable.
- **`POST /simulate`** – Phase A: Creator. Request body:
  - `webshop_id` (int): Must be `1380`.
  - `products` (array): Each item must include `id`, `sku`, `name`, `shop_id`, **`supplier_id`** (required), `selling_price`, `purchase_price`, `current_stock_on_hand`, `product_delivery_time`. Only product IDs in the whitelist (§5) are simulated; others are skipped.
  - Response: `record_counts`, `api_payloads.sales`, `api_payloads.buy_orders`. Caller (e.g. Retool) should POST these to Optiply Public API in batches with delay (e.g. 100–200 ms between requests).
- **`POST /maintain?webshop_id=1380`** – Phase B: Maintainer. Shifts all dates forward to today. Query param `webshop_id` must be `1380`.

## 7. Development
- **Entrypoints**: `src/main.py` (FastAPI app), `src/simulation.py` (demand + supply loop), `src/database.py` (PostgreSQL wipe/insert/maintenance).
- **Run locally**: Set `DATABASE_URL`, then `pip install -r requirements.txt`, `uvicorn src.main:app --host 0.0.0.0 --port 8080`. Docker also uses port 8080.
- **Tests**: `pytest tests/ -v` from the `demo-account-simulator` directory (see README).
- **Context**: This repo may be edited by both Cursor and Gemini CLI; keep this file (`docs/CONTEXT.md`) and the root README in sync when changing API or behaviour.

## 8. Implementation status (what’s been done)

This section records what has been implemented so far. **Update it whenever you add or change behaviour.**

- **API & safety**
  - `POST /simulate` requires `supplier_id` on each product; only whitelisted product IDs (§5) are simulated (others skipped with a warning).
  - Product ID whitelist is defined in `src/main.py` as `DEMO_PRODUCT_WHITELIST`.
- **Database**
  - Stock inserts use per-row execute in batches (2000 rows); `database.wipe_and_insert_stocks()` runs wipe + insert in a single transaction to avoid partial state on failure.
  - `stocks` is assumed to have unique constraint on `(product_id, date)`; see comment in `database.py` if your schema differs.
- **Robustness**
  - `GET /health` returns 503 if `DATABASE_URL` is unset or DB unreachable.
  - Optional `FAIL_FAST_NO_DB=1` makes the app exit at startup when `DATABASE_URL` is missing (e.g. for Cloud Run).
  - `/simulate` and `/maintain` return 503 when DB is not configured; errors are caught and returned as 500 with detail.
- **Docs & tooling**
  - Root README, `.env.example`, API contract (§6), and Development (§7) in this file. Seasonal formula typo fixed.
  - [RETOOL.md](RETOOL.md) describes workflow and batching/throttling for the Public API; includes Cloud Run service URL and auth note. It also contains the **human-readable description of the Retool sandbox workflow** (what `retool-workflow-sandbox.json` represents)—use that instead of reading the JSON.
  - `retool-workflow-sandbox.json` (if present in `docs/`) is a Retool Workflows export (re-import only); the readable workflow logic is in RETOOL.md.
  - [DEPLOY-CLOUDRUN.md](DEPLOY-CLOUDRUN.md) describes how to build and deploy to Google Cloud Run (APIs, Artifact Registry, deploy command, DB connectivity).
  - [PLAN.md](PLAN.md) and [GEMINI.md](GEMINI.md) give Gemini CLI (and others) the improvement plan and spec references.
  - **Context file**: This spec lives in `docs/CONTEXT.md`; when you make changes, update this file (especially §8) so we know what’s going on.
- **Tests**
  - Unit tests in `tests/test_simulation.py` for `DemandEngine` (base demand, daily demand for Stable Fast/Slow, Obsolete, New Launch, Seasonal) and `SupplyChainSimulator` (return shape, stocks/sales/buy_orders, `supplier_id` in buy_orders). Run: `pytest tests/ -v` from `demo-account-simulator`.
- **Port**
  - App and Docker use port 8080; Dockerfile respects Cloud Run’s `PORT` env var (default 8080).
- **Cloud Run**
  - Deploy steps and service URL documentation: see [DEPLOY-CLOUDRUN.md](DEPLOY-CLOUDRUN.md). Retool should use the Cloud Run service URL as the engine base URL (see [RETOOL.md](RETOOL.md)).

# Demo Account Simulator — Shared Context for Handoff or Other Tools

Use this document to bring another tool or team up to speed. It consolidates project purpose, architecture, implementation status, and the **Python (Cloud Run) vs Retool Workflows** decision.

---

## 1. Purpose and open decision

**Goal:** A “digital twin” demo environment for **Optiply Shop 1380** (Cosmetics) so sales can show a live-looking dashboard with 365 days of synthetic inventory, sales, and purchase orders. Two phases:

- **Phase A (Creator):** Generate 365 days of synthetic history (stocks, sales, buy_orders) from product archetypes.
- **Phase B (Maintainer):** Nightly job that shifts all dates forward so the demo always looks “current.”

**Open question:** Is **Python on Google Cloud Run** or **Retool Workflows** (or a hybrid) the better approach? This doc gives enough context to compare and decide.

---

## 2. Current architecture (hybrid)

As implemented today:

| Layer | Technology | Responsibility |
|-------|------------|----------------|
| **Database** | PostgreSQL (Optiply DB) | Source of truth: `stocks`, `sell_orders`, `buy_orders`, product data. |
| **Logic / compute** | **Python (FastAPI)** | Demand math (archetypes), 365-day daily loop, ROP/reorder logic, batch stock inserts. Runs as a service (local or **Cloud Run**). |
| **Orchestration** | **Retool Workflows** | Triggers (webhook, cron), fetches products (with `supplier_id`) from DB, calls Python `POST /simulate`, then POSTs returned `api_payloads` (sales, buy_orders) to **Optiply Public API** in batches with delay. Nightly: calls `POST /maintain`. |
| **Optiply Public API** | External | Creates `sell_orders` and `buy_orders` in the real system (webhooks, business logic). Not used for high-volume `stocks`; those go direct to DB from Python. |

So: **Python does the simulation and direct DB writes for stocks; Retool runs the workflow and talks to the Public API for orders.**

---

## 3. Option comparison: Python Cloud Run vs Retool Workflows

### Option A — Python on Cloud Run (current engine)

**What it is:** The simulation runs in a FastAPI app in a Docker container on Google Cloud Run. Retool (or any HTTP client) calls `POST /simulate` and `POST /maintain?webshop_id=1380`.

**Pros**

- **Heavy math in one place:** All demand archetypes (seasonal, trend, stockout, new launch, etc.) and the 365-day loop live in Python (pandas/numpy); easy to test and version.
- **Performance:** One service does the full simulation and batch-inserts stocks (2000 rows/batch) via SQL; no round-trips per day.
- **Portable:** Same code runs locally or on Cloud Run; no Retool lock-in for the core logic.
- **Observability:** Logs, health checks, and (if you add them) metrics in one service.

**Cons**

- **Two systems:** You maintain both a Python app (repo, Docker, Cloud Run, `DATABASE_URL`, secrets) and Retool workflows.
- **DB access:** Python needs a direct PostgreSQL connection (and possibly VPC/Cloud SQL setup) for high-volume stock inserts.
- **Deploy steps:** Build image, push to Artifact Registry, deploy to Cloud Run (see `docs/DEPLOY-CLOUDRUN.md`).

### Option B — Retool Workflows only (no Python service)

**What it would be:** Reimplement (or simplify) the simulation inside Retool: SQL + JavaScript/Python blocks, loops over “days,” and writes to DB and/or Optiply API.

**Pros**

- **Single platform:** No separate service to deploy or secure; everything in Retool.
- **No Cloud Run or Docker:** Fewer moving parts if your team already uses Retool for everything.
- **UI-driven:** Non-devs can tweak workflow logic in the Retool UI.

**Cons**

- **Complexity in Retool:** A 365-day loop with demand math, ROP, and batching is heavy for workflow blocks; harder to unit test and keep in version control.
- **Rate and limits:** Many Retool blocks (e.g. REST loops with delay) may make a full 365-day run slow or hit workflow limits.
- **Stocks volume:** Pushing thousands of stock rows via Retool (e.g. one REST or SQL call per batch) is possible but more awkward than one Python process doing batch SQL.

### Option C — Hybrid (current)

**What it is:** Python does simulation + stock writes; Retool triggers the Python API and posts the returned sales/buy_orders to the Optiply Public API.

**Pros**

- **Separation of concerns:** Math and bulk DB in Python; orchestration, scheduling, and “call Optiply API” in Retool.
- **Spec alignment:** Matches the original spec (Python engine + Retool triggers and API posting).

**Cons**

- Same as Option A for running a second system (Python/Cloud Run) and DB connectivity.

**Recommendation (for the “still deciding” context):** If you want minimal ops and everything inside Retool, try Option B for a **small** subset (e.g. one product, 30 days) to see if Retool is comfortable. If you need the full 365-day, multi-archetype simulation and fast stock inserts, **Option A/C (Python on Cloud Run + Retool)** is the better fit; the current codebase is already built for that.

---

## 4. Technical summary (for either approach)

### Product whitelist (demo safety)

Only these product IDs may be used for the demo (shop 1380):

`28666283, 28666286, 28666287, 28666288, 28666289, 28666290, 28666291, 28666292, 28666293, 28666294, 28666295, 28666296, 28666297, 28666298, 28666299, 28666300, 28666301, 28666302, 28666303, 28666304, 28666305, 28666306, 28666307, 28666308, 28666309, 28666310, 28666311, 28666312, 28666313, 28666314, 28666315, 28666316`

### Demand archetypes (from product name)

Archetype is parsed from `webshop_products.name`, e.g. `"Product (Seasonal Summer)"` → `"Seasonal Summer"`. Supported shapes:

- **Stable Fast / Stable Slow** — constant mean ±15% noise.
- **Seasonal (Summer/Winter/Holiday/Micro)** — Gaussian peak; optional monthly payday modulation.
- **Positive / Negative Trend** — linear ramp in last 120 days.
- **Stockout Prone** — 2× demand; ROP cut to 80% of lead-time demand in last 90 days.
- **New Launch (Success/Flop)** — zero until day -30, then 2.5× or 0.5×.
- **Outlier, Lumpy, Sporadic, Obsolete, Container, Multi-Supplier, Step Change** — see `docs/CONTEXT.md` §3.

### API contract (Python service)

- **`GET /`** — `{"status":"active","shop":1380}`  
- **`GET /health`** — 200 + `{"status":"healthy"}` or 503 if DB missing/unreachable  
- **`POST /simulate`** — Body: `{ "webshop_id": 1380, "products": [ { "id", "sku", "name", "shop_id", "supplier_id", "selling_price", "purchase_price", "current_stock_on_hand", "product_delivery_time" }, ... ] }`. Response: `record_counts`, `api_payloads.sales`, `api_payloads.buy_orders`. Caller must POST those to Optiply Public API in batches with delay (e.g. 100–200 ms).  
- **`POST /maintain?webshop_id=1380`** — Shifts `placed`, `expected_delivery_date`, and `stocks.date` forward by the lag to today. Query param required.

### Phase B (Maintainer) SQL (spec)

Only these columns are shifted (no `completed`):

- **sell_orders:** `placed`  
- **buy_orders:** `placed`, `expected_delivery_date`  
- **stocks:** `date`  

Lag = `CURRENT_DATE - MAX(date)` (from stocks) or equivalent from orders.

### Data flow (Creator)

1. Fetch products for `webshop_id = 1380`, whitelisted product IDs, include `supplier_id`.
2. Call Python `POST /simulate` with that payload.
3. Python: wipes demo stocks (soft delete), runs 365-day simulation, batch-inserts stocks (direct SQL), returns `api_payloads.sales` and `api_payloads.buy_orders`.
4. Caller (e.g. Retool) POSTs `api_payloads.sales` and `api_payloads.buy_orders` to Optiply Public API in batches with delay.

---

## 5. Repo layout (demo-account-simulator)

```
demo-account-simulator/
├── README.md                 # Setup, run, test, deploy, Retool pointers
├── .env.example              # DATABASE_URL, optional FAIL_FAST_NO_DB
├── requirements.txt          # fastapi, uvicorn, pandas, numpy, sqlalchemy, psycopg2-binary, pydantic, python-dotenv, httpx, pytest
├── Dockerfile                # Python 3.11, port from PORT env (Cloud Run)
├── src/
│   ├── main.py               # FastAPI app, /simulate, /maintain, /health, whitelist, Query(webshop_id)
│   ├── simulation.py        # DemandEngine, SupplyChainSimulator (365-day loop, archetypes)
│   └── database.py          # DatabaseManager: wipe_stocks, batch_insert_stocks, wipe_and_insert_stocks, run_maintenance_shift, check_connection
├── tests/
│   ├── conftest.py           # Pytest path setup
│   └── test_simulation.py    # DemandEngine + SupplyChainSimulator unit tests
└── docs/
    ├── CONTEXT.md            # Full spec, API, implementation status (source of truth)
    ├── RETOOL.md             # Retool workflow description, batching/throttling, Cloud Run URL
    ├── DEPLOY-CLOUDRUN.md    # gcloud steps: APIs, Artifact Registry, build, deploy, DB connectivity
    ├── PLAN.md               # Improvement plan and high-level flow
    ├── GEMINI.md             # Gemini CLI context (@CONTEXT.md, @PLAN.md)
    └── SHARED-CONTEXT.md     # This file
```

---

## 6. Implementation status (as of this doc)

- **API:** `supplier_id` required on products; only whitelisted IDs simulated; `POST /maintain` uses query param `webshop_id` (FastAPI `Query()`).
- **DB:** Single-transaction wipe + insert for stocks; maintenance updates only `placed` and `expected_delivery_date` (no `completed`).
- **Robustness:** `/health`, optional `FAIL_FAST_NO_DB=1`, 503 when DB missing, try/except around simulate and maintain.
- **Docs:** CONTEXT.md (§8), RETOOL.md, DEPLOY-CLOUDRUN.md, PLAN.md, GEMINI.md.
- **Tests:** pytest for DemandEngine and SupplyChainSimulator (`pytest tests/ -v` from project root).
- **Deploy:** Dockerfile uses `PORT`; deploy steps in `docs/DEPLOY-CLOUDRUN.md`.

---

## 7. How to use this with another tool

- **Copy this file** into the other tool’s context or attach it as a single “project brief.”
- **For “Python vs Retool”:** Use §3 (Option A/B/C) and §4–§5 to compare effort, ops, and performance.
- **For implementation:** Use §4 (API, whitelist, Phase B SQL) and §5 (repo layout) plus `docs/CONTEXT.md` and `docs/RETOOL.md` for full detail.
- **For deployment:** Point to `docs/DEPLOY-CLOUDRUN.md` and the Dockerfile; Cloud Run service URL is the base for `POST /simulate` and `POST /maintain`.

If you change the architecture (e.g. move logic into Retool), update `docs/CONTEXT.md` §8 and this file so the next handoff stays accurate.

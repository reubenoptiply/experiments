# Retool Workflow Integration

This document describes how Retool Workflows should call the simulation engine and post results to the Optiply Public API.

**About `retool-workflow-sandbox.json`:** That file (if present in `docs/`) is a Retool Workflows export (workflow name: "reuben-sandbox"). It is not meant to be read as documentation. The human-readable description of what the workflow does and how it fits the simulation engine is in this file (sections below). Keep the JSON only if you need to re-import the workflow into Retool; you can delete it if you no longer need the export and rely on this doc.

## Sandbox workflow (what the JSON represents)

High-level purpose: a sandbox Retool workflow that orchestrates the demo simulation—fetching shop/product data, calling the simulation engine (or in-workflow Python), and posting sales/buy orders to the Optiply Public API.

**Flow (from the export):**

1. **Trigger:** Webhook (start).
2. **Paths that feed the simulation / API:**
   - **Get shop data** (SQL, Optiply_ProductionDB) → **Simulate supply chain** (Python block) → **Orchestrate execution** (JS) → **Post sales** (loop over Optiply Public API, batch size 1, delay 10 ms, ignore iteration errors).
   - **Get products** (SQL) → **Code** (JS/Python to shape payload) → **Loop** (REST to Optiply Public API, batch 1, delay 1 ms).
3. **Reporting / metrics:** Several SQL blocks (e.g. `get_products_and_costs`, `get_buy_counts`, `get_sales_metrics`) and code blocks (Python/JS) that aggregate or transform data, plus loops that POST to the Optiply Public API where needed.

**Resources used:** Optiply_ProductionDB (SQL), Optiply Public API (REST), JavascriptQuery, PythonQuery. Batch config in loops: typically `batchSize: 1`, `delayInMs: 1` or `10`, `iterationErrorConfig: ignore`.

**Alignment with [CONTEXT.md](CONTEXT.md):** For the canonical "Creator" flow, the workflow should: (1) query products for `webshop_id = 1380` and whitelisted product IDs, including `supplier_id`; (2) call the simulation engine's `POST /simulate` with that payload; (3) take `api_payloads.sales` and `api_payloads.buy_orders` and POST them to the Optiply Public API in batches with delay (see "Batching and throttling" below).

## Service URL (Cloud Run)

When the engine is deployed to Google Cloud Run, use the service URL as the base for all requests (e.g. `https://demo-account-simulator-xxx-REGION.run.app`). Set this URL in your Retool workflow resource or environment variable.

- If the Cloud Run service was deployed **with** `--allow-unauthenticated`, call the URL directly.
- If the service requires authentication, configure Retool to send an identity token (e.g. use a GCP service account and generate an OIDC token for the request). See [DEPLOY-CLOUDRUN.md](DEPLOY-CLOUDRUN.md) for deploy options.

## Workflow overview

1. **Trigger**: Webhook or manual run for full reset; cron (nightly) for maintenance.
2. **Full reset (Phase A)**  
   - Query products for `webshop_id = 1380` and product IDs in the [whitelist](CONTEXT.md#5-constraints--safety). Include `supplier_id` in the query.  
   - Call `POST /simulate` with body: `{ "webshop_id": 1380, "products": [ ... ] }`.  
   - Use the response `api_payloads.sales` and `api_payloads.buy_orders` to POST to the Optiply Public API (sell_orders and buy_orders endpoints).  
3. **Maintenance (Phase B)**  
   - Call `POST /maintain?webshop_id=1380` (e.g. nightly).

## Batching and throttling (Public API)

To respect Optiply Public API rate limits:

- **Batch size**: Send sell_orders and buy_orders in small batches (e.g. 10–50 items per request if the API allows batching; otherwise one at a time).
- **Delay**: Add a delay between requests (e.g. 100–200 ms). Use Retool's loop block "delay between batches" or equivalent.
- **Error policy**: Configure the loop to continue on iteration error (e.g. log and skip) or retry with backoff, so one failed POST does not abort the whole run.

The simulation engine returns all payloads in one response; it does not call the Public API itself. Retool is responsible for throttled posting.

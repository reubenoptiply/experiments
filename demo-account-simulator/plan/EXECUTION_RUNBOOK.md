# Execution Runbook — Finish by Tomorrow

**Goal:** Working Creator + Maintainer workflows in Retool. **Budget:** ~2.5–3.5 hours (one focused session or two shorter ones).

Use this as a tick list. Keep the [Builder Guide](./Retool_Workflow_Builder_Guide_—_Creator_&_Maintainer.md) and [plan/README.md](./README.md) open for copy-paste.

---

## Pre-flight (do once, ~10 min)

- [ ] **Retool app** — Workflow (not App) with a **PostgreSQL** resource connected to the demo DB.
- [ ] **Product whitelist** — Confirm the 32 product IDs with your DB. Builder Guide uses the list in Block 2; if your whitelist differs, update `fetch_products` IN clause once and reuse everywhere.
- [ ] **Environment** — `access_token` (Optiply Bearer) available for `replan_agenda` (Retool env/secret or workflow variable).
- [ ] **Files at hand** — `retool-blocks/` (simulate_stocks.py, fetch_product_meta.sql, fetch_daily_sales.sql, build_stocks_insert.js, insert_stocks.sql, soft_delete_stocks.sql), `plan/README.md`, Builder Guide.

---

## Phase 1: Creator — Data layer (T1 + T2) — ~1 hr

Build in this order. **Test after each step** so you don’t carry forward broken state.

### 1. Trigger + fetch (15 min)

- [ ] Add **Webhook** trigger → name: `startTrigger`.
- [ ] Add **SQL** blocks → `fetch_product_meta` and `fetch_daily_sales`, run after `startTrigger`.  
  Copy from [retool-blocks/fetch_product_meta.sql](../retool-blocks/fetch_product_meta.sql) and [retool-blocks/fetch_daily_sales.sql](../retool-blocks/fetch_daily_sales.sql).
- [ ] Run workflow (trigger → fetch_product_meta + fetch_daily_sales). Confirm product rows and daily sales columns as expected.

### 2. Simulation (T1) (25 min)

- [ ] Add **Python** block → name: `simulate_stocks`, runs after `fetch_product_meta` and `fetch_daily_sales`.
- [ ] Paste the **entire** contents of [retool-blocks/simulate_stocks.py](../retool-blocks/simulate_stocks.py). The script expects `fetch_product_meta.data` and `fetch_daily_sales.data` (Retool exposes prior blocks by name).
- [ ] **Quick test:** Run trigger → fetch_product_meta + fetch_daily_sales → simulate_stocks. Check output: `data.stocks` is an array; rows have `product_id`, `product_uuid`, `webshop_id`, `webshop_uuid`, `on_hand`, `date` (e.g. `YYYY-MM-DD 00:00:02`). Row count ≈ 32 × 366.

### 3. Stocks write path (20 min)

- [ ] Add **SQL** block → name: `soft_delete_stocks`, runs after `simulate_stocks`.  
  Copy from [retool-blocks/soft_delete_stocks.sql](../retool-blocks/soft_delete_stocks.sql).
- [ ] Add **JavaScript** block → name: `build_stocks_insert`, runs after `soft_delete_stocks`.  
  Copy from [retool-blocks/build_stocks_insert.js](../retool-blocks/build_stocks_insert.js). It reads `simulate_stocks?.data?.stocks` and returns `{ sql_values }`.
- [ ] Add **SQL** block → name: `insert_stocks`, runs after `build_stocks_insert`.  
  Use [retool-blocks/insert_stocks.sql](../retool-blocks/insert_stocks.sql) and bind the VALUES to `{{ build_stocks_insert.data.sql_values }}` (or your block's equivalent).
- [ ] Run the chain: trigger → … → soft_delete_stocks → build_stocks_insert → insert_stocks. Verify in DB: `SELECT COUNT(*) FROM stocks WHERE webshop_id = 1380 AND deleted_at IS NULL` matches expected rows.

**Checkpoint:** Creator data path works: fetch_product_meta + fetch_daily_sales → simulate_stocks → soft_delete → build_stocks_insert → insert_stocks. No orchestration yet.

---

## Phase 2: Creator — Orchestration (T3) — ~30 min

- [ ] Add **JavaScript** block → name: `all_done`, runs after `insert_stocks`.  
  Code: `return { done: true };` (join gate).
- [ ] Add **SQL** block → name: `setup_promotions`, runs after `all_done`.  
  Stub: `SELECT 'promotions_stub' AS status;` (Builder Guide Block 10).
- [ ] Add **SQL** (or API) block → name: `setup_composed_products`, runs after `setup_promotions`.  
  Stub: `SELECT 'composed_stub' AS status;` (Builder Guide Block 11).
- [ ] Add **REST / Loop** block → name: `replan_agenda`, runs after `setup_composed_products`.  
  Loop over unique `supplier_uuid` from `fetch_products.data`. Each iteration: POST to  
  `https://api.optiply.com/api/buy-order/v2/{{ webshop_uuid }}/supplier/{{ item.supplier_uuid }}/order-moment/re-plan`  
  with header `Authorization: Bearer {{ access_token }}`, body `{}`. Delay 200 ms between iterations.
- [ ] Set **simulation_end_date** when Creator runs: in a small JS block at the start (or in `all_done`) set a Retool workflow/global variable, e.g. `simulation_end_date = new Date().toISOString().slice(0,10)` (YYYY-MM-DD). Maintainer will read this.
- [ ] **Full Creator run:** Trigger webhook → wait for end. Confirm no failed blocks; check DB for 11,680 stocks.

**Checkpoint:** Creator end-to-end works with stubs.

---

## Phase 3: Maintainer (T4) — ~35 min

- [ ] **Duplicate** the Creator workflow. Rename to “Maintainer” (or “Demo Maintainer”).
- [ ] Change **trigger:** Cron `0 2 * * *` (02:00 UTC) and keep a webhook for manual runs.
- [ ] **Replace** the block that runs after `all_done`: remove `setup_promotions` and `setup_composed_products` from the chain. Add in order:
  - **SQL** → name: `delete_manual_buy_orders`, runs after `all_done`.  
    Copy from Builder Guide Block 10 (Maintainer). Use `{{ simulation_end_date }}` (the variable you set in Creator); if stored in a different place (e.g. config table), reference that.
  - **SQL** → name: `restore_phased_out_products`, runs after `delete_manual_buy_orders`.  
    Copy from Builder Guide Block 11 (SQL fallback).
  - **replan_agenda** — same as Creator (loop over suppliers, POST re-plan). Runs after `restore_phased_out_products`.
- [ ] Ensure Maintainer can read `simulation_end_date` (same Retool env/global or config table the Creator writes).
- [ ] **Test:** Run Maintainer via webhook. Confirm no failed blocks; optionally run Creator once to set `simulation_end_date`, then run Maintainer and check that manual buy orders after that date are soft-deleted.

**Checkpoint:** Maintainer runs end-to-end; cron is set for 02:00 UTC.

---

## If you’re short on time

| Priority | Do this | Skip or stub |
|----------|--------|-------------------------------|
| **Must have by tomorrow** | Phase 1 + Phase 2 (Creator full run) + Phase 3 (Maintainer structure + manual test) | replan_agenda can be a no-op (e.g. return success) if API not ready; promotions/composed already stubbed |
| **If only 1.5 hrs** | Phase 1 only: fetch → lag → simulate → soft_delete → build_stocks_insert → insert_stocks. Test with one full run. | Do Phase 2–3 tomorrow |
| **If Retool insert is awkward** | Keep build_stocks_insert; use Retool’s bulk insert or 2k-row chunking (see CONTEXT.md) as a temporary workaround until dynamic SQL works |

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Python block “fetch_products is not defined” | Ensure `simulate_all_products` runs after `calculate_lag` and that Retool injects prior block results; some UIs use `blocks.fetch_products.data`. |
| insert_stocks fails (query too long / invalid) | Chunk: split `stocks` into batches of 2000 in a JS loop, run multiple INSERTs; or use a Retool bulk-insert pattern. |
| lag_days is NULL | No stocks yet; use `COALESCE((CURRENT_DATE - MAX(date)::date), 0)` in calculate_lag so shifts get 0. |
| simulation_end_date not set for Maintainer | Creator must set it (JS or config table) when it runs; Maintainer reads the same variable/row. |

---

## Done-by-tomorrow definition

- [ ] **Creator:** Webhook → fetch_products → calculate_lag → (simulate + shift_sell + shift_buy) → soft_delete_stocks → build_stocks_insert → insert_stocks → all_done → setup_promotions (stub) → setup_composed_products (stub) → replan_agenda (or no-op). Stocks table has 11,680 rows for shop 1380.
- [ ] **Maintainer:** Duplicate of Creator up to all_done, then delete_manual_buy_orders → restore_phased_out_products → replan_agenda. Cron 02:00 UTC; webhook tested.
- [ ] **simulation_end_date** set by Creator and read by Maintainer.

Stubs (promotions, composed, exact replan_agenda body) can stay as-is until schemas/APIs are confirmed.

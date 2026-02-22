# Retool blocks (canonical)

Copy these files into your Retool Workflow. They form the **Creator** data path for the demo account simulator (Shop 1380).

**Order and dependencies**

1. **fetch_product_meta.sql** — Products for webshop 1380 (32 whitelisted IDs). Run first (e.g. after trigger).
2. **fetch_daily_sales.sql** — Daily units sold per product (last 366 days). Run in parallel or after fetch_product_meta.
3. **simulate_stocks.py** — Python block. Inputs: `fetch_product_meta.data`, `fetch_daily_sales.data`. Output: `{ stocks: [...] }`.
4. **soft_delete_stocks.sql** — Soft-delete existing stocks for shop 1380. Run after simulate_stocks.
5. **build_stocks_insert.js** — JS block. Input: `simulate_stocks.data.stocks`. Output: `{ sql_values }` for the INSERT.
6. **insert_stocks.sql** — Uses `{{ build_stocks_insert.data.sql_values }}`. Run after build_stocks_insert.

See [plan/README.md](../plan/README.md) and [EXECUTION_RUNBOOK.md](../plan/EXECUTION_RUNBOOK.md) for full workflow setup (orchestration, Maintainer, etc.).

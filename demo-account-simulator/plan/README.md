# Plan: Pure Retool Workflow Demo Simulator

This folder holds the **brief, tech plan, tickets, and build guide** for the fully Retool-workflow-based demo account simulator (no Python Cloud Run).

- **Want to finish by tomorrow?** → Use **[EXECUTION_RUNBOOK.md](./EXECUTION_RUNBOOK.md)** for a time-boxed, tick-list execution plan (~2.5–3.5 hrs).
- **Otherwise** → Start with [IMPLEMENTATION_ORDER.md](./IMPLEMENTATION_ORDER.md) for the recommended build order.

## Quick start

1. **T1** — Use the **canonical** simulation script and SQL in [retool-blocks/](../retool-blocks/): `fetch_product_meta.sql`, `fetch_daily_sales.sql`, [simulate_stocks.py](../retool-blocks/simulate_stocks.py). In Retool, create SQL blocks for product meta and daily sales, then a **Python** block (e.g. `simulate_stocks`) that uses `fetch_product_meta.data` and `fetch_daily_sales.data`; paste [simulate_stocks.py](../retool-blocks/simulate_stocks.py).
2. **T2** — Add SQL blocks (fetch_product_meta, fetch_daily_sales → simulate_stocks → soft_delete_stocks → build_stocks_insert → insert_stocks). For `insert_stocks`, use [build_stocks_insert.js](../retool-blocks/build_stocks_insert.js) and [insert_stocks.sql](../retool-blocks/insert_stocks.sql).
3. **T3 / T4** — See IMPLEMENTATION_ORDER and the [Retool Workflow Builder Guide](./Retool_Workflow_Builder_Guide_—_Creator_&_Maintainer.md).

(An older synthetic-demand script is in [archive/](./archive/) for reference.)

## JS block: `build_stocks_insert`

Add a **JavaScript** block named `build_stocks_insert` that runs after `simulate_all_products` (or after `soft_delete_stocks` if you prefer). It turns the `stocks` array into one `VALUES (...),(...),...` string so the next SQL block can run a single INSERT.

**Input:** `simulate_stocks.data.stocks` (or the block that holds `{ stocks: [...] }`).

**Output:** Set a Retool workflow variable (e.g. `stocks_values_sql`) or return an object that the `insert_stocks` SQL block can reference.

```javascript
// Escape single quotes for SQL
function esc(s) {
  if (s == null) return 'NULL';
  return "'" + String(s).replace(/'/g, "''") + "'";
}

const stocks = simulate_stocks?.data?.stocks ?? [];
const values = stocks.map(r =>
  `(${r.product_id}, ${esc(r.product_uuid)}, ${r.webshop_id}, ${esc(r.webshop_uuid)}, ${r.on_hand}, ${esc(r.date)})`
).join(',\n');

const sql = `INSERT INTO stocks\n  (product_id, product_uuid, webshop_id, webshop_uuid, on_hand, date)\nVALUES\n  ${values}`;

return { stocks_values_sql: sql, row_count: stocks.length };
```

In the **insert_stocks** SQL block, run the query as **raw SQL** and use:
`{{ build_stocks_insert.data.stocks_values_sql }}`
(if Retool allows multi-line; otherwise use a resource that executes the returned string).

> Some Retool setups run the SQL block with a single query string. If your app expects a query **resource** with a parameter, bind the parameter to `build_stocks_insert.data.stocks_values_sql` so the full INSERT is sent as one statement.

## Where `simulation_end_date` lives

- **Creator:** When the Creator workflow runs, set `simulation_end_date` to the last date in the simulated range (e.g. `start_date + 364 days` or the run date). Store it in a Retool global variable or a small config table so the Maintainer can read it.
- **Maintainer:** Reads `simulation_end_date` to decide which buy_orders are “manual” (e.g. `placed > simulation_end_date`) and deletes them in `delete_manual_buy_orders` before re-running the simulation and shifts.

## Files in this folder

| File | Purpose |
|------|--------|
| [EXECUTION_RUNBOOK.md](./EXECUTION_RUNBOOK.md) | Time-boxed tick list to finish Creator + Maintainer (~2.5–3.5 hrs) |
| [IMPLEMENTATION_ORDER.md](./IMPLEMENTATION_ORDER.md) | Dependency order and how to start (T1→T2→T3→T4) |
| [Epic_Brief_—_Optiply_Demo_Account_Simulator.md](./Epic_Brief_—_Optiply_Demo_Account_Simulator.md) | Scope and success criteria |
| [Tech_Plan_—_Optiply_Demo_Account_Simulator.md](./Tech_Plan_—_Optiply_Demo_Account_Simulator.md) | Architecture and constraints |
| [T1](T1__Build_the_Simulation_Python_Block_(Retool).md) / [T2](T2__Creator_Workflow_—_SQL_Data_Layer_(stocks_+_sell_orders).md) / [T3](T3__Creator_Workflow_—_Promotions,_Composed_Products_+_Orchestration.md) / [T4](T4__Build_the_Maintainer_Workflow_(nightly_cron).md) | Per-phase tickets and acceptance criteria |
| [Retool_Workflow_Builder_Guide_—_Creator_&_Maintainer.md](./Retool_Workflow_Builder_Guide_—_Creator_&_Maintainer.md) | Block-by-block SQL/code and wiring for Creator & Maintainer |
| [archive/](./archive/) | Superseded script (synthetic demand); canonical blocks are in [retool-blocks/](../retool-blocks/) |

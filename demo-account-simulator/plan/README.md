# Plan: Pure Retool Workflow Demo Simulator

This folder holds the **brief, tech plan, tickets, and build guide** for the fully Retool-workflow-based demo account simulator (no Python Cloud Run). Start with [IMPLEMENTATION_ORDER.md](./IMPLEMENTATION_ORDER.md) for the recommended build order.

## Quick start

1. **T1** — Use the ready-to-paste simulation script: [retool_simulation_block.py](./retool_simulation_block.py). In Retool, create a **Python** block named `simulate_all_products`, paste the script, and set its input to `fetch_products.data`.
2. **T2** — Add SQL blocks (fetch_products → calculate_lag → parallel: simulate + shift_sell_orders + shift_buy_orders → soft_delete_stocks → insert_stocks). For `insert_stocks`, use the JS helper below to build the INSERT from `simulate_all_products.data.stocks`.
3. **T3 / T4** — See IMPLEMENTATION_ORDER and the [Retool Workflow Builder Guide](./Retool_Workflow_Builder_Guide_—_Creator_&_Maintainer.md).

## JS block: `build_stocks_insert`

Add a **JavaScript** block named `build_stocks_insert` that runs after `simulate_all_products` (or after `soft_delete_stocks` if you prefer). It turns the `stocks` array into one `VALUES (...),(...),...` string so the next SQL block can run a single INSERT.

**Input:** `simulate_all_products.data.stocks` (or the block that holds `{ stocks: [...] }`).

**Output:** Set a Retool workflow variable (e.g. `stocks_values_sql`) or return an object that the `insert_stocks` SQL block can reference.

```javascript
// Escape single quotes for SQL
function esc(s) {
  if (s == null) return 'NULL';
  return "'" + String(s).replace(/'/g, "''") + "'";
}

const stocks = simulate_all_products?.data?.stocks ?? [];
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
| [IMPLEMENTATION_ORDER.md](./IMPLEMENTATION_ORDER.md) | Dependency order and how to start (T1→T2→T3→T4) |
| [retool_simulation_block.py](./retool_simulation_block.py) | Paste-ready Retool Python block (T1) |
| [Epic_Brief_—_Optiply_Demo_Account_Simulator.md](./Epic_Brief_—_Optiply_Demo_Account_Simulator.md) | Scope and success criteria |
| [Tech_Plan_—_Optiply_Demo_Account_Simulator.md](./Tech_Plan_—_Optiply_Demo_Account_Simulator.md) | Architecture and constraints |
| T1 / T2 / T3 / T4 tickets | Per-phase acceptance criteria |
| [Retool_Workflow_Builder_Guide_—_Creator_&_Maintainer.md](./Retool_Workflow_Builder_Guide_—_Creator_&_Maintainer.md) | Block-by-block build steps |

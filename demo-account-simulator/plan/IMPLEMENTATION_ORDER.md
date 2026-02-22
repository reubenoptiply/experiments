# Implementation Order — Pure Retool Workflow Approach

This folder contains the Epic Brief, Tech Plan, tickets (T1–T4), and Builder Guide for building the demo simulator **entirely in Retool Workflows** (no Python Cloud Run service). Follow this order to get to a working Creator + Maintainer quickly.

## Dependency order

```
T1 (Simulation Python block)  ← start here
    ↓
T2 (Creator SQL layer: fetch, lag, shifts, soft_delete, insert_stocks)
    ↓
T3 (Creator orchestration: all_done, promotions stub, composed stub, replan_agenda)
    ↓
T4 (Maintainer: duplicate Creator, add delete_manual_buy_orders, restore_phased_out_products, cron)
```

## How to start

1. **T1 first** — The simulation is the foundation. Use the ready-to-paste script in `retool_simulation_block.py` (or the inline summary in the Builder Guide). In Retool: create a **Python** block named `simulate_all_products`, paste the script, and wire its input to `fetch_products.data`. Run with one product to verify output shape and no numpy/pandas.
2. **T2 next** — In Retool, create the Creator workflow and add blocks in this order: `fetch_products` (SQL) → `calculate_lag` (SQL) → in parallel: `simulate_all_products` (Python), `shift_sell_orders` (SQL), `shift_buy_orders` (SQL). Then `soft_delete_stocks` (SQL) → `insert_stocks` (SQL). For `insert_stocks`, use the `build_stocks_insert` JS block + SQL pattern described in `plan/README.md` (or Builder Guide Block 8).
3. **T3** — Add `all_done` (JS join gate), `setup_promotions` (stub), `setup_composed_products` (stub), `replan_agenda` (REST loop). Wire the webhook trigger and optional `dry_run`.
4. **T4** — Duplicate the Creator workflow to create the Maintainer; change trigger to Cron (02:00 UTC) + webhook for testing. Replace blocks after `all_done` with `delete_manual_buy_orders`, `restore_phased_out_products`, then `replan_agenda`. Set `simulation_end_date` (see Builder Guide “Shared variables”).

## What’s in this folder

| File | Purpose |
|------|---------|
| `Epic_Brief_—_Optiply_Demo_Account_Simulator.md` | Why we’re doing this; scope; success criteria |
| `Tech_Plan_—_Optiply_Demo_Account_Simulator.md` | Architecture, data model, block list, constraints (no numpy), failure modes |
| `T1__Build_the_Simulation_Python_Block_(Retool).md` | Ticket: port simulation to Retool Python; output only `stocks`; data quality fixes |
| `T2__Creator_Workflow_—_SQL_Data_Layer_(stocks_+_sell_orders).md` | Ticket: fetch_products, calculate_lag, shifts, soft_delete, insert_stocks |
| `T3__Creator_Workflow_—_Promotions,_Composed_Products_+_Orchestration.md` | Ticket: all_done, promotions/composed stubs, replan_agenda, full wiring |
| `T4__Build_the_Maintainer_Workflow_(nightly_cron).md` | Ticket: Maintainer workflow; delete manual BOs; restore phased-out products |
| `Retool_Workflow_Builder_Guide_—_Creator_&_Maintainer.md` | Step-by-step: every block’s type, name, code/query, and wiring |
| `retool_simulation_block.py` | **Ready-to-paste** Retool Python block (pure Python, no numpy/pandas) |
| `IMPLEMENTATION_ORDER.md` | This file |

## Whitelist note

The Builder Guide’s `fetch_products` IN list includes `28666284` and `28666285`. The legacy repo CONTEXT whitelist has 32 IDs starting at `28666283` and then `28666286`… (omits 28666284, 28666285). Confirm with your DB which 32 product IDs are the canonical demo set and use that list in `fetch_products`.

## Open items (from Builder Guide)

- **Promotions** — `setup_promotions` is a stub until the promotions table INSERT schema is confirmed.
- **Composed products** — `setup_composed_products` is a stub until schema/API is confirmed.
- **Restore phased-out** — `restore_phased_out_products` uses a SQL fallback; Optiply API endpoint for re-enabling products is TBD.
- **replan_agenda** — Confirm POST body (empty or payload) with Optiply.
- **simulation_end_date** — Stored when Creator runs (e.g. Retool global variable or small config table); Maintainer reads it for `delete_manual_buy_orders`.

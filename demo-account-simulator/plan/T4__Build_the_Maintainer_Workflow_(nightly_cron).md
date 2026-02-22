# T4: Build the Maintainer Workflow (nightly cron)

## What

Build the Maintainer Retool Workflow that runs every night to keep the demo account current: shift all dates forward, undo manual changes made by account execs, and replan the purchase agenda.

## Scope

**In:**
- `startTrigger`: cron schedule (02:00 UTC daily); also triggerable manually via webhook for testing
- `calculate_lag` SQL: `SELECT (CURRENT_DATE - MAX(date)::date) AS lag_days FROM stocks WHERE webshop_id = 1380 AND deleted_at IS NULL` — single source of truth for the shift amount
- `simulate_all_products` Python: same block as Creator — regenerates `stocks[]` for all 32 products based on today's date (runs in parallel with shifts)
- `shift_sell_orders` SQL: shift `placed` on `sell_orders` and `sell_order_lines` by `lag_days` (parallel with `shift_buy_orders` and simulation)
- `shift_buy_orders` SQL: shift `placed`, `expected_delivery_date`, `completed` on `buy_orders` and `buy_order_lines` by `lag_days`
- `soft_delete_stocks` SQL: `UPDATE stocks SET deleted_at = NOW() WHERE webshop_id = 1380 AND deleted_at IS NULL` (runs after simulation completes)
- `insert_stocks` SQL: insert fresh stock rows from simulation output — same pattern as Creator
- `delete_manual_buy_orders` SQL: soft-delete BOs where `placed > simulation_end_date` and `webshop_id = 1380` (these were placed manually by account execs during demos); also delete their lines
- `restore_phased_out_products` SQL + API: detect whitelisted products where `status != 'enabled'`; restore via Optiply API (endpoint **TBD**) or (fallback) direct SQL if no API endpoint is available
- `replan_agenda` REST loop: `POST https://api.optiply.com/api/buy-order/v2/{webshop_uuid}/supplier/{supplier_uuid}/order-moment/re-plan` per supplier; runs last

**Out:**
- Simulation logic, Creator workflow blocks
- Reorder point / safety stock changes (not reset — only phased-out status and manual BOs are undone)

## Key implementation notes

- `simulate_all_products`, `shift_sell_orders`, and `shift_buy_orders` all run in parallel after `calculate_lag` — they are independent
- `soft_delete_stocks` runs after `simulate_all_products` completes; `insert_stocks` runs after `soft_delete_stocks`
- `delete_manual_buy_orders` runs after the shift blocks complete (so it doesn't interfere with the lag calculation)
- `simulation_end_date` is stored as a Retool environment variable set by the Creator workflow at run time — the Maintainer reads it to distinguish simulated vs. manual BOs
- If `lag_days = 0` (Maintainer runs same day as Creator), all shift blocks are no-ops — safe
- If `lag_days < 0` (data is somehow ahead of today), log a warning and skip shifts

## Acceptance criteria

- After nightly run, `MAX(date)` in stocks for shop 1380 equals `CURRENT_DATE` (fresh rows inserted by simulation)
- Sell orders and buy orders have dates consistent with the shifted stocks (no date mismatches)
- Any buy orders placed manually by account execs (placed > `simulation_end_date`) are soft-deleted
- Any products phased out during a demo are restored to `enabled` status
- Agenda shows current, realistic purchase advice after replan
- Workflow is idempotent — running it twice on the same day produces the same result

## Dependencies

- T2 (sell/buy orders must exist to shift; `simulation_end_date` variable set by Creator)
- T1 (simulation block reused here)

## Spec references
- `spec:ed4445ac-7cc8-4778-912d-6824d7f919b1/8258a28c-e4aa-4648-a4a8-a1a439255d6e` — Tech Plan §1 (maintenance decisions, failure modes), §3 (Maintainer block table)
- `spec:ed4445ac-7cc8-4778-912d-6824d7f919b1/105d70ee-f216-496b-9b12-a809e156019b` — Epic Brief (success criteria)

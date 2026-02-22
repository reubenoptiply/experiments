# T2: Creator Workflow — SQL Data Layer (stocks + sell orders)

## What

Build the SQL data layer of the Creator Retool Workflow: fetch products, calculate the dynamic lag, shift existing sell/buy order dates to end at today, and regenerate stock history via soft-delete + re-insert from simulation output.

## Scope

**In:**
- `fetch_products` SQL block: query `webshop_products` + `supplier_products` for all 32 whitelisted product IDs in shop 1380; return `id`, `uuid`, `webshop_uuid`, `name`, `selling_price`, `purchase_price`, `supplier_id`, `supplier_uuid`, `delivery_time`
- `calculate_lag` SQL block: `SELECT (CURRENT_DATE - MAX(date)::date) AS lag_days FROM stocks WHERE webshop_id = 1380 AND deleted_at IS NULL`
- `shift_sell_orders` SQL block (runs in parallel with `shift_buy_orders`):
  ```sql
  UPDATE sell_orders SET placed = placed + (lag_days * INTERVAL '1 day'), updated_at = NOW() WHERE webshop_id = 1380;
  UPDATE sell_order_lines SET placed = placed + (lag_days * INTERVAL '1 day'), updated_at = NOW() WHERE webshop_id = 1380;
  ```
- `shift_buy_orders` SQL block (runs in parallel with `shift_sell_orders`):
  ```sql
  UPDATE buy_orders SET placed = placed + (lag_days * INTERVAL '1 day'), expected_delivery_date = expected_delivery_date + (lag_days * INTERVAL '1 day'), completed = CASE WHEN completed IS NOT NULL THEN completed + (lag_days * INTERVAL '1 day') ELSE NULL END, updated_at = NOW() WHERE webshop_id = 1380;
  UPDATE buy_order_lines SET updated_at = NOW() WHERE webshop_id = 1380;
  ```
- `soft_delete_stocks` SQL block: `UPDATE stocks SET deleted_at = NOW() WHERE webshop_id = 1380 AND deleted_at IS NULL`
- `insert_stocks` SQL block: single large `INSERT INTO stocks (product_id, product_uuid, webshop_id, webshop_uuid, on_hand, date) VALUES (...)` — all ~11,680 rows from simulation output; no `ON CONFLICT` needed (rows were soft-deleted)
- Block sequence: `fetch_products` → `calculate_lag` → [`shift_sell_orders` + `shift_buy_orders` + `simulate_all_products`] (parallel) → `soft_delete_stocks` → `insert_stocks`

**Out:**
- Buy orders, promotions, composed products, agenda replan (those are T3)
- Simulation logic (T1)

## Key implementation notes

- The product whitelist (`28666283`–`28666316`, 32 IDs) must be hardcoded in the `fetch_products` WHERE clause as a safety guard
- `shift_sell_orders` and `shift_buy_orders` run in parallel — they are independent; `simulate_all_products` also runs in parallel with them (it only needs `fetch_products` output)
- `soft_delete_stocks` must complete before `insert_stocks` — sequential dependency
- `insert_stocks` uses a single SQL statement with all rows as VALUES tuples — no `ON CONFLICT` needed since rows are soft-deleted first
- `simulation_end_date` (= `CURRENT_DATE` at run time) must be stored as a Retool workflow variable — the Maintainer uses it to detect manually placed BOs
- `lag_days` must be passed as a variable to the shift blocks — store as a Retool workflow variable after `calculate_lag`

## Acceptance criteria

- `fetch_products` returns exactly 32 rows with all required fields including `uuid`, `webshop_uuid`, and `supplier_uuid`
- After `shift_sell_orders`, `MAX(placed)` on `sell_orders` for shop 1380 equals `CURRENT_DATE` (or within 1 day)
- After `shift_buy_orders`, `MAX(placed)` on `buy_orders` for shop 1380 equals `CURRENT_DATE` (or within 1 day)
- After `soft_delete_stocks`, all stocks for shop 1380 have `deleted_at IS NOT NULL`
- After `insert_stocks`, exactly 32 × 365 = 11,680 rows exist with `deleted_at IS NULL`
- Stock values are all ≥ 0; dates span from `TODAY - 365` to `TODAY`

## Dependencies

- T1 must be complete (simulation output feeds this workflow)

## Spec references
- `spec:ed4445ac-7cc8-4778-912d-6824d7f919b1/8258a28c-e4aa-4648-a4a8-a1a439255d6e` — Tech Plan §2 (stocks schema), §3 (Creator block table)

# T3: Creator Workflow — Promotions, Composed Products + Orchestration

## What

Complete the Creator Retool Workflow: add the `all_done` join gate, set up promotions and composed products (stubs until schemas confirmed), trigger the agenda replan per supplier, and wire all blocks into a single connected workflow with a webhook trigger.

**No buy order API calls** — buy orders already exist in the DB and are date-shifted by T2.

## Scope

**In:**
- `all_done` JS block: join gate that waits for `shift_sell_orders`, `shift_buy_orders`, and `insert_stocks` to all complete before proceeding; returns `{ done: true }`
- `setup_promotions` SQL block: insert promotion records for Seasonal and Influencer Spikes archetype products (⚠️ schema TBD — stub with `SELECT 'promotions_stub'` until confirmed)
- `setup_composed_products` SQL/API block: configure assembly/production product relationships (⚠️ schema/method TBD — stub until confirmed)
- `replan_agenda` REST loop: `POST https://api.optiply.com/api/buy-order/v2/{webshop_uuid}/supplier/{supplier_uuid}/order-moment/re-plan` — loop over unique suppliers from `fetch_products` output; `delayInMs: 200`; runs last
- Full workflow wiring: connect all blocks (T2 + T3) with correct success edges; webhook `startTrigger` with optional `dry_run` param

**Out:**
- Simulation logic (T1)
- SQL data layer — shifts + stocks (T2)
- Maintainer workflow (T4)

**Explicitly removed (no longer in scope):**
- `post_buy_orders` REST loop — not needed, buy orders exist in DB
- `post_buy_order_lines` REST loop — not needed

## Block wiring (Creator complete)

```
startTrigger
  └─► fetch_products
        └─► calculate_lag
              ├─► simulate_all_products ──► soft_delete_stocks ──► insert_stocks ──┐
              ├─► shift_sell_orders ────────────────────────────────────────────────┤
              └─► shift_buy_orders ─────────────────────────────────────────────────┤
                                                                                    ▼
                                                                               all_done (JS)
                                                                                    └─► setup_promotions
                                                                                          └─► setup_composed_products
                                                                                                └─► replan_agenda
```

## Key implementation notes

- `all_done` JS block: in Retool, set "Run after" to `shift_sell_orders`, `shift_buy_orders`, and `insert_stocks` — this is how Retool joins parallel branches
- `replan_agenda` loop: deduplicate `supplier_uuid` from `fetch_products.data` before looping — each supplier gets exactly one replan call
- `replan_agenda` URL uses `webshop_uuid` from `fetch_products` (constant for shop 1380: `b6aba3eb-4412-4b3c-a261-2073f7fdb152`)
- Stubs for `setup_promotions` and `setup_composed_products` must return success (not error) so the workflow continues — use `SELECT 'stub'`
- `dry_run` param: if `startTrigger.body.dry_run === true`, skip all SQL writes and API calls; log counts only

## Acceptance criteria

- `all_done` block fires only after all three parallel branches complete
- `replan_agenda` returns 200 for each unique supplier
- Full Creator workflow runs end-to-end from webhook trigger to `replan_agenda` without manual intervention
- Promotions stub logs a warning and continues (does not block workflow)
- Composed products stub logs a warning and continues (does not block workflow)
- `dry_run: true` runs the full workflow without writing to DB or calling the API

## Dependencies

- T1 (simulation Python block must be complete — its output feeds `insert_stocks`)
- T2 (all shift + stocks blocks must complete before `all_done`; `simulation_end_date` variable set)

## Spec references
- `spec:ed4445ac-7cc8-4778-912d-6824d7f919b1/f63ddcf2-39cd-498e-bd67-08a5208ee422` — Builder Guide (Creator block map, Block 9 `all_done`, Block 12 `replan_agenda`)
- `spec:ed4445ac-7cc8-4778-912d-6824d7f919b1/8258a28c-e4aa-4648-a4a8-a1a439255d6e` — Tech Plan §3 (component diagram)
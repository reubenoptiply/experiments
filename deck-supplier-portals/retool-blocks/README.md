# Deck Supplier Portal — Retool blocks (canonical)

Copy these files into your Retool Workflows and Database resources to implement the **Core Flows** for Deck Supplier Portal Ordering (epic: Supplier Portal Ordering Implementation).

**Context:** [context-and-implementation.md](../context-and-implementation.md), [tech-plan-retool.md](../tech-plan-retool.md).

---

## 1. Setup: Retool DB schema

Run once in your **Retool Database** resource:

- **schema_deck_tables.sql** — Creates `deck_jobs`, `supplier_portal_config`, `sku_mappings`.

Then seed pilot data: one row in `supplier_portal_config` (supplier_id, supplier_name, source_guid, is_active) and rows in `sku_mappings` as needed.

---

## 2. Workflow A: deck-submit-order (manual trigger)

Triggered by the app when the user clicks "Send Selected to Supplier Portal". Inputs: `bo_ids` (array), `customer_id`.

**Order and dependencies:**

| Step | Block | Resource | Notes |
|------|--------|----------|--------|
| 1 | fetch_bo_line_items_optiply.sql | Optiply Postgres | Bind `bo_ids`. Returns line items with quantity, unit_price, optiply_sku, supplier_sku. |
| 2 | fetch_supplier_portal_config.sql | Retool DB | Bind `supplier_id` (from first BO or grouped). Get source_guid. |
| 3 | fetch_sku_mappings.sql | Retool DB | Bind `supplier_id`. |
| 4 | transform_bo_to_deck_items.js | — | Inputs: `fetch_bo_line_items_optiply.data`, `fetch_sku_mappings.data`, `currencySymbol` (e.g. "€"). Output: `{ items }`. |
| 5 | check_in_flight_jobs.sql | Retool DB | Bind `supplier_id`. If returns any rows, block or return error. |
| 6 | insert_deck_job.sql | Retool DB | Bind supplier_id, customer_id, bo_ids (JSON array), items (from step 4). Status = connecting. |
| 7 | build_ensure_connection_body.js | — | Inputs: source_guid (from config), username/password (env vars). Output: `{ body }`. |
| 8 | **HTTP: POST Deck** | — | URL: `https://sandbox.deck.co/api/v1/jobs/submit` (or live). Headers: `x-deck-client-id`, `x-deck-secret`. Body: step 7. |
| 9 | update_deck_job.sql | Retool DB | Set job_guid from Deck response (response.job_guid) WHERE id = inserted job id. |

**Group by supplier:** A batch may span multiple suppliers. Run the flow once per supplier group (group BOs by supplier_id, then for each group run steps 2–9). One Deck job per supplier.

---

## 3. Workflow B: deck-webhook-receiver (webhook trigger)

Trigger: **Webhook**. Give the workflow’s webhook URL to Deck. Deck POSTs all results here.

**Order and dependencies:**

| Step | Block | Notes |
|------|--------|--------|
| 1 | parse_webhook_dispatch.js | Input: webhook body (e.g. `startTrigger.body`). Output: `action`, `job_guid`, `access_token`, `output`, `error`. |
| 2 | **Branch on** `parse_webhook_dispatch.data.action` | EnsureConnection \| AddItemsToCart \| Error \| MfaRequired \| Unknown. |
| 3a | **If EnsureConnection:** get_deck_job_by_guid.sql (Retool DB) | Bind job_guid from payload. Get deck_job row. |
| 3b | update_deck_job.sql | Set access_token, status = 'adding_items'. |
| 3c | build_add_items_to_cart_body.js | Inputs: access_token (from webhook output), items (from deck_job.items). |
| 3d | **HTTP: POST Deck** AddItemsToCart | Body from step 3c. Store new job_guid from response for next webhook. |
| 3e | update_deck_job.sql | Set new job_guid for AddItemsToCart job (so next webhook correlates). |
| 4a | **If AddItemsToCart:** get_deck_job_by_guid.sql | Bind job_guid. |
| 4b | compute_add_items_status.js | Input: webhook output. Output: status ('completed' \| 'needs_review'), failedCount, priceMismatchCount. |
| 4c | update_deck_job.sql | Set results = output, status = from step 4b. |
| 4d | build_close_connection_body.js | Input: access_token from deck_job. |
| 4e | **HTTP: POST Deck** CloseConnection | No webhook returned. |
| 4f | **Slack / notify** | Summary: items added, failed, price mismatches. |
| 5a | **If Error:** get_deck_job_by_guid.sql, update_deck_job.sql | status = 'failed', error_message = error.error_message. Notify. |
| 5b | **If MfaRequired:** update status = 'failed', error_message = 'MFA required'. Notify (pilot does not support MFA). |

---

## 4. Scheduled workflow: deck-job-timeout-check

Trigger: **Schedule** (e.g. every 15 minutes).

| Step | Block | Notes |
|------|--------|--------|
| 1 | stuck_jobs_timeout.sql | Retool DB. Returns jobs where status IN ('connecting','adding_items') AND updated_at < now() - 10 min. |
| 2 | **Loop** over rows | For each: mark_job_failed_timeout.sql with id, error_message = 'Timeout: no webhook received'. |
| 3 | **Slack** | Alert with list of timed-out job ids. |

---

## 5. App: Approved BOs and filters

- **submitted_bo_ids.sql** (Retool DB) — Returns BO IDs already in deck_jobs (not failed). Use to filter approved BOs in the app or in fetch_approved_bos_optiply.
- **fetch_approved_bos_optiply.sql** (Optiply DB) — Approved BOs. Optionally exclude IDs from submitted_bo_ids (e.g. in a combined query or filter in UI).

Adjust Optiply table/column names in the SQL files to match your Postgres schema (`buy_orders`, `buy_order_lines`, `products`, `suppliers`).

---

## 6. File reference

| File | Type | Purpose |
|------|------|--------|
| schema_deck_tables.sql | SQL (Retool DB) | DDL for deck_jobs, supplier_portal_config, sku_mappings |
| fetch_approved_bos_optiply.sql | SQL (Optiply) | Approved BOs list |
| fetch_bo_line_items_optiply.sql | SQL (Optiply) | Line items for given bo_ids |
| submitted_bo_ids.sql | SQL (Retool DB) | BO IDs already submitted |
| fetch_supplier_portal_config.sql | SQL (Retool DB) | Config by supplier_id |
| fetch_sku_mappings.sql | SQL (Retool DB) | SKU mapping by supplier_id |
| check_in_flight_jobs.sql | SQL (Retool DB) | In-flight jobs for supplier (block duplicate submit) |
| transform_bo_to_deck_items.js | JS | BO lines → Deck items (sku, quantity, expected_price) |
| build_ensure_connection_body.js | JS | EnsureConnection request body |
| build_add_items_to_cart_body.js | JS | AddItemsToCart request body |
| build_close_connection_body.js | JS | CloseConnection request body |
| insert_deck_job.sql | SQL (Retool DB) | Insert job (status connecting) |
| update_deck_job.sql | SQL (Retool DB) | Update job_guid, access_token, status, results, error_message |
| get_deck_job_by_guid.sql | SQL (Retool DB) | Lookup job by job_guid (webhook) |
| parse_webhook_dispatch.js | JS | Parse webhook → action, job_guid, access_token, output, error |
| compute_add_items_status.js | JS | output.items → status completed/needs_review |
| stuck_jobs_timeout.sql | SQL (Retool DB) | Jobs stuck > 10 min |
| mark_job_failed_timeout.sql | SQL (Retool DB) | Mark job failed (timeout) |

---

## 7. Environment variables (Retool)

- `DECK_CLIENT_ID`, `DECK_SECRET` — Deck API (do not hardcode).
- `DECK_SUPPLIER_USERNAME`, `DECK_SUPPLIER_PASSWORD` — Pilot supplier portal credentials (or per-customer in production).
- `SLACK_WEBHOOK_URL` — For timeout and error notifications.

Use sandbox (`https://sandbox.deck.co/api/v1/jobs/submit`) or live (`https://live.deck.co/api/v1/jobs/submit`) as appropriate.

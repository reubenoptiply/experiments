# Deck Supplier Portal — Retool blocks (canonical)

Copy these files into your Retool Workflows and Database resources to implement the **Core Flows** for Deck Supplier Portal Ordering (epic: Supplier Portal Ordering Implementation).

**Context:** [context-and-implementation.md](../context-and-implementation.md), [tech-plan-retool.md](../tech-plan-retool.md).

**Flowcharts:** [WORKFLOW_FLOWCHARTS.md](./WORKFLOW_FLOWCHARTS.md) — index and where each Deck API is called. Detailed flows: [WORKFLOW_A_deck_submit_order.md](./WORKFLOW_A_deck_submit_order.md), [WORKFLOW_B_deck_webhook_receiver.md](./WORKFLOW_B_deck_webhook_receiver.md), [WORKFLOW_C_deck_job_timeout_check.md](./WORKFLOW_C_deck_job_timeout_check.md).

**WWW26 fair demo (Hairaction):** [WORKFLOW_WWW26_Demo.md](./WORKFLOW_WWW26_Demo.md) — hardcoded BO, email, app polling; static wireframes in [../www26-demo/](../www26-demo/).

---

## 1. Setup: Retool DB schema

Run once in your **Retool Database** resource:

- **schema_deck_tables.sql** — Creates `deck_jobs`, `deck_supplier_portal_config`, `deck_sku_mappings`.

Then seed pilot data: one row in `deck_supplier_portal_config` (supplier_id, supplier_name, source_guid, is_active) and rows in `deck_sku_mappings` as needed.

---

## 2. Workflow A: deck-submit-order (manual trigger)

Triggered by the app when the user clicks "Send to Supplier Portal" for a single BO. Inputs: `bo_id`, `customer_id`, `supplier_id`. **One job per buy order** (each BO can have many line items / BOLs).

### Triggering efficiently (no editing SQL with BO IDs)

Pass the **selected BO IDs from the app** into the workflow as **Workflow run input** (trigger parameters). The workflow then binds those parameters in every block — you never paste BO IDs into SQL.

**1. In the Retool App**

- Add a **Table** that loads approved BOs (e.g. query `fetch_approved_bos_optiply` or an Optiply resource).
- Enable **Row selection** (multi-select) on the table.
- Add a **Button** “Send Selected to Supplier Portal” that **runs the workflow** with the selection as input.

**2. Workflow trigger: define input parameters**

In Workflow A, open the **trigger** block and add **Workflow input** (or “Run workflow” input) parameters, for example:

| Parameter   | Type   | Description |
|------------|--------|-------------|
| `bo_id`      | string | One buy order ID |
| `customer_id` | string | Customer ID for this BO |
| `supplier_id` | string | Supplier ID for this BO |

**3. App → Workflow: what to pass**

From the app, when running the workflow, pass:

- **Single selection:** `bo_id`: `table1.selectedRow.bo_id`, `customer_id`: `table1.selectedRow.customer_id`, `supplier_id`: `table1.selectedRow.supplier_id`.
- **Multiple selection (one job per BO):** Run the workflow once per row (e.g. loop over `table1.selectedRows`) passing each row's `bo_id`, `customer_id`, `supplier_id`.

**4. In the workflow: bind blocks to trigger input**

In each block, bind parameters to the **trigger’s output** (often `trigger.data` or the name of your trigger block, e.g. `startTrigger`). Retool Workflows expose run input differently by version; typical patterns:

- **If the trigger exposes run input as an object:**  
  - `bo_id` → `{{ startTrigger.bo_id }}` (or `startTrigger.runInput.bo_id`)  
  - `supplier_id` → `{{ startTrigger.supplier_id }}`  
  - `customer_id` → `{{ startTrigger.customer_id }}`

- **SQL blocks:** bind `:bo_id` → `{{ startTrigger.bo_id }}`, `:supplier_id` and `:customer_id` similarly. **insert_deck_job** uses a single `:bo_id`, not an array.

- **JS blocks:** set query inputs `lineItems`, `skuMappings`, etc. to the previous block outputs; for values that come from the app (e.g. `currencySymbol`), you can use `{{ startTrigger.currencySymbol }}` or a constant.

Result: the app chooses which BO(s); the workflow receives one `bo_id` per run and no SQL is edited with IDs.

**Order and dependencies:**

| Step | Block | Resource | Notes |
|------|--------|----------|--------|
| 1 | fetch_bo_line_items_optiply.sql | Optiply Postgres | Bind `bo_id`. Returns line items (BOLs) with quantity, unit_price, optiply_sku, supplier_sku. |
| 2 | fetch_supplier_portal_config.sql | Retool DB | Bind `supplier_id`. Get source_guid. |
| 3 | fetch_sku_mappings.sql | Retool DB | Bind `supplier_id`. |
| 4 | transform_bo_to_deck_items.js | — | Inputs: `fetch_bo_line_items_optiply.data`, `fetch_sku_mappings.data`, `currencySymbol` (e.g. "€"). Output: `{ items }`. |
| 5 | check_in_flight_jobs.sql | Retool DB | Bind `supplier_id`. If returns any rows, block or return error. |
| 6 | insert_deck_job.sql | Retool DB | Bind supplier_id, customer_id, bo_id (single), items (from step 4). Status = connecting. |
| 7 | build_ensure_connection_body.js | — | Inputs: source_guid (from config), username/password (env vars). Output: `{ body }`. |
| 8 | **HTTP: POST Deck** | — | URL: `https://sandbox.deck.co/api/v1/jobs/submit` (or live). Headers: `x-deck-client-id`, `x-deck-secret`. Body: step 7. |
| 9 | update_deck_job.sql | Retool DB | Set job_guid from Deck response (response.job_guid) WHERE id = inserted job id. |

**One BO per run:** Each workflow run processes one buy order. To send multiple BOs, run the workflow once per BO from the app (e.g. loop over selected rows).

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

- **submitted_bo_ids.sql** (Retool DB) — Returns bo_id list already in deck_jobs (not failed). Filter approved BOs in the app so already-submitted BOs are excluded or disabled.
- **fetch_approved_bos_optiply.sql** (Optiply DB) — Approved BOs. Filter in app by submitted_bo_ids if needed.

Adjust Optiply table/column names in the SQL files to match your Postgres schema (`buy_orders`, `buy_order_lines`, `products`, `suppliers`).

---

## 6. File reference

| File | Type | Purpose |
|------|------|--------|
| schema_deck_tables.sql | SQL (Retool DB) | DDL for deck_jobs, deck_supplier_portal_config, deck_sku_mappings |
| fetch_approved_bos_optiply.sql | SQL (Optiply) | Approved BOs list |
| fetch_bo_line_items_optiply.sql | SQL (Optiply) | Line items for one bo_id |
| submitted_bo_ids.sql | SQL (Retool DB) | bo_id list already submitted |
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
- `WWW26_DEMO_NOTIFY_EMAIL` (optional) — Inbox for the WWW26 demo Send Email block ([WORKFLOW_WWW26_Demo.md](./WORKFLOW_WWW26_Demo.md)).

Use sandbox (`https://sandbox.deck.co/api/v1/jobs/submit`) or live (`https://live.deck.co/api/v1/jobs/submit`) as appropriate.

---

## 8. WWW26 demo blocks (Hairaction / fair recording)

| File | Purpose |
|------|---------|
| [www26_hardcoded_buy_order.js](./www26_hardcoded_buy_order.js) | Hardcoded BO-2026-0412 line items + Deck `items` payload |
| [www26_merge_stored_items_for_email.js](./www26_merge_stored_items_for_email.js) | Job `items` JSON → named `lineItems` for email |
| [build_www26_email_html.js](./build_www26_email_html.js) | Transactional HTML email `subject` + `html` |
| [www26_format_results_for_table.js](./www26_format_results_for_table.js) | Merge `results` + catalog → table rows for the app |
| [fetch_www26_latest_demo_job.sql](./fetch_www26_latest_demo_job.sql) | Poll latest job where `customer_id = 'www26-demo'` |

Full wiring: **[WORKFLOW_WWW26_Demo.md](./WORKFLOW_WWW26_Demo.md)**.

**Sample Retool DB seed (Hairaction):** [sample_data_hairaction_deck.sql](./sample_data_hairaction_deck.sql) — `deck_supplier_portal_config` + example `deck_jobs` row.

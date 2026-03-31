# Workflow WWW26: Demo App & Deck flow (Hairaction)

**Purpose:** Fair-demo flow for **WWW26**: one-click submit from a Retool App, real **Deck live** calls to **hairaction.nl**, progress UI with Deck screenshot placeholders, results from the real **AddItemsToCart** webhook, and a **Send Email** notification.

**Spec:** Core Flows — WWW26 Demo App & Video (`bbcb6e32-fb11-4a55-9c48-dbf8c05d0ac5`).

**Architecture note:** Deck remains **async + webhook-driven**. The “single streamlined” demo is one **operator journey**: the app triggers a **submit workflow** (like Workflow A) and **polls** `deck_jobs`; the existing **webhook workflow** (Workflow B) completes AddItemsToCart, CloseConnection, and — for demo jobs only — sends email.

---

## Prerequisites

1. **Retool DB** — `schema_deck_tables.sql` applied.
2. **`deck_supplier_portal_config`** — one row for the demo supplier, e.g. `supplier_id = 'hairaction-demo'`, `supplier_name = 'Hairaction'`, `source_guid` = real Deck source GUID for hairaction.nl.
3. **Environment variables** — `DECK_CLIENT_ID`, `DECK_SECRET`, portal credentials (e.g. `DECK_SUPPLIER_USERNAME` / `DECK_SUPPLIER_PASSWORD` or Hairaction-specific vars), **live** Deck base URL: `https://live.deck.co/api/v1/jobs/submit`.
4. **`WWW26_DEMO_NOTIFY_EMAIL`** — operator inbox for the Send Email block (spec: hardcode for demo; prefer env var in Retool secrets).

---

## Workflow D: `www26-deck-submit-demo` (manual / run from app)

Mirror **Workflow A** ([WORKFLOW_A_deck_submit_order.md](./WORKFLOW_A_deck_submit_order.md)) but **replace BO fetch + transform** with hardcoded data.

| Step | Block | Notes |
|------|--------|--------|
| 1 | **JavaScript** `www26_hardcoded_buy_order.js` | No inputs. Output: `itemsForDeck`, `demoSupplierId`, `demoCustomerId`, `boRef`, display fields. |
| 2 | **SQL** `fetch_supplier_portal_config.sql` | Bind `:supplier_id` → `{{ www26_hardcoded_buy_order.data.demoSupplierId }}`. |
| 3 | **SQL** `check_in_flight_jobs.sql` | Same `supplier_id` binding; optional for demo — you may skip or relax for booth resets. |
| 4 | **SQL** `insert_deck_job.sql` | `supplier_id` → demo supplier id; `customer_id` → `www26-demo`; `bo_id` → `BO-2026-0412` (or `{{ www26_hardcoded_buy_order.data.boRef }}`); `items` → `{{ www26_hardcoded_buy_order.data.itemsForDeck }}` as JSON. |
| 5 | **JavaScript** `build_ensure_connection_body.js` | `source_guid` from config row; `username` / `password` from env (Hairaction demo credentials). |
| 6 | **HTTP POST** Deck | Same headers as production; **EnsureConnection** body. |
| 7 | **SQL** `update_deck_job.sql` | Set `job_guid` from Deck response for the inserted row. |
| 8 | **Return data to app** | e.g. `{ deck_job_id: insert.data.id }` via a small JS block or workflow return value. |

Deck then calls **Workflow B** (shared webhook URL) as today.

---

## Workflow B extension: Send Email for demo jobs only

After **CloseConnection** (and optional Slack) on the **AddItemsToCart** path, add a **Branch**:

- Condition: `{{ get_deck_job_by_guid.data.customer_id }} === 'www26-demo'` (adjust to your query output shape, e.g. first row).

**If true:**

| Block | Notes |
|--------|--------|
| **JavaScript** `www26_merge_stored_items_for_email.js` | Input `storedItems` = `{{ get_deck_job_by_guid.data.items }}` (or first row’s `items`). Output `lineItems` with product names. |
| **JavaScript** `build_www26_email_html.js` | `boRef` = job `bo_id`; `portalName` = `hairaction.nl`; `portalReviewUrl` = `https://www.hairaction.nl`; `lineItems` = previous block’s `lineItems`; `deckItems` = `{{ parse_webhook_dispatch.data.output.items }}`; optional `supplierBrand` = `Hairaction`. |
| **Send Email** (Retool) | To: `{{ environment.variables.WWW26_DEMO_NOTIFY_EMAIL }}` or literal; Subject: `{{ build_www26_email_html.data.subject }}`; Body: HTML = `{{ build_www26_email_html.data.html }}`. |

**Product names in the email:** Use **`www26_merge_stored_items_for_email.js`** so `lineItems` includes names while `deck_jobs.items` stays Deck-shaped (`sku`, `quantity`, `expected_price`).

---

## Retool App: “Optiply — Supplier Portal Automation (Demo)”

### Data

| Query | Type | Purpose |
|-------|------|---------|
| `www26_hardcoded_buy_order` | JS | Header, summary cards, line items table (initial view). |
| `fetch_www26_latest_demo_job` | SQL | Poll every 2–5 s while `submitInProgress` is true. |
| `www26_format_results_for_table` | JS | Inputs: `lineItems` from hardcoded query; `resultsJson` from latest job `results`. Drives results **Table**. |
| `www26_merge_stored_items_for_email` | JS | Input `storedItems` from polled job’s `items`; feeds email preview. |
| `build_www26_email_html` | JS | `deckItems` from `latestJob.results.items` (or full `results` — see `www26_format_results_for_table` parsing). Preview when job is terminal. |

### Submit button

- **Run workflow** `www26-deck-submit-demo` (no inputs, or pass a `run_id` for logging).
- Set **temporary state** `submitStartedAt = Date.now()`, `submitInProgress = true`.

### Progress UX (spec timing)

Use **job status** from `fetch_www26_latest_demo_job` plus optional **client timers**:

| UI step | When to show |
|---------|----------------|
| 1 — Connecting | `status === 'connecting'` OR first ~3s after submit if row not yet updated |
| 2 — Adding items | `status === 'adding_items'` |
| 3 — Results | `status` in `completed`, `needs_review`, `failed` — table from **real** `results` |
| 4 — Email | After step 3, show banner + run `build_www26_email_html` for preview |

**Screenshot carousel:** Use 2–3 images (Deck dashboard exports). Store in Retool **Files** or static URLs; rotate with a **timer** query (refresh interval 1s) and `index = floor((now - start) / 3000) % n` in a **JavaScript** query, or a **Custom component**. If the webhook completes before the carousel finishes, **delay revealing the results table** until `elapsed >= 11000` ms OR `status` terminal for >2s — spec: prefer syncing slideshow with results.

### Constants

- `customer_id` for demo jobs must be exactly **`www26-demo`** so SQL + Workflow B branch match.

---

## Assets checklist (before Loom)

| Asset | Action |
|-------|--------|
| Deck agent screenshots | Export from Deck; plug into carousel |
| Live SKUs | Validate on hairaction.nl; edit `LINE_ITEMS` in `www26_hardcoded_buy_order.js` |
| Env / secrets | Deck live, portal login, `WWW26_DEMO_NOTIFY_EMAIL` |

**Talking points** — use the script in the spec (pain → one click → agent → results → email → value).

---

## File reference (this repo)

| File | Role |
|------|------|
| [www26_hardcoded_buy_order.js](./www26_hardcoded_buy_order.js) | Hardcoded BO + Deck `items` |
| [build_www26_email_html.js](./build_www26_email_html.js) | Email subject + HTML |
| [www26_format_results_for_table.js](./www26_format_results_for_table.js) | App results table rows |
| [www26_merge_stored_items_for_email.js](./www26_merge_stored_items_for_email.js) | Job `items` JSON → `lineItems` for email |
| [fetch_www26_latest_demo_job.sql](./fetch_www26_latest_demo_job.sql) | Poll latest demo job |

Static HTML wireframes (reference only): [../www26-demo/reference/](../www26-demo/reference/).

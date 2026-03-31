# Plan: Admin panel page — trigger supplier-portal PO (Deck)

**Goal:** An internal tool where operators enter a **Buy Order (BO) id**, pick a **supplier** (with Deck portal automation enabled), see the **supplier website**, and **submit** to run the Deck flow (EnsureConnection → AddItemsToCart → CloseConnection via existing workflows).

**Primary UI path — Retool Apps:** Retool is a **drag-and-drop builder** (canvas + components + queries). You do **not** need a separate React/Vue app for v1: create a **Retool App**, wire **Resource queries** (SQL / REST / Workflow), and bind component properties with `{{ }}` — see **Phase 4 (Retool)** below.

**Prerequisites:** Deck **Retool Workflows** accept **`bo_id`**, **`customer_id`**, **`supplier_id`** — see [deck-submit-order-REVIEW.md](./deck-submit-order-REVIEW.md) and [retool-blocks/WORKFLOW_A_deck_submit_order.md](./retool-blocks/WORKFLOW_A_deck_submit_order.md).

---

## Phase 0 — Access and resources

1. **Retool:** Create a dedicated App (e.g. “Deck — Supplier portal submit”) in the right **Space**; restrict with **Retool permissions** / groups so only internal users see it.
2. **Resources:** Retool **Database** (Retool DB for `deck_*` tables), **Database** or **REST** for Optiply Postgres / APIs (BO lines, summary), **Workflow** resource or **Webhook** to run Workflow A — match how your org already connects Retool to Optiply.
3. **Secrets:** Deck client id/secret and portal credentials live in **Retool environment variables** or **Secrets**, referenced from Workflow / REST blocks — never in App client-side strings that ship to the browser as plain text if your org has stricter policies (Retool still evaluates queries server-side for resources).

---

## Phase 1 — Data: supplier list + portal URL for the UI

Today `deck_supplier_portal_config` has `supplier_id`, `supplier_name`, `source_guid`, `is_active` — **no public portal URL**. To “automatically show the website” you need a **display URL** (and optionally a **label**).

1. **Extend Retool DB** (or Optiply DB if you move config there):

   ```sql
   ALTER TABLE deck_supplier_portal_config
     ADD COLUMN IF NOT EXISTS portal_base_url TEXT;

   COMMENT ON COLUMN deck_supplier_portal_config.portal_base_url IS
     'HTTPS URL shown in admin iframe/link, e.g. https://www.hairaction.nl';
   ```

2. **Backfill** each active supplier (Hairaction → `https://www.hairaction.nl`, etc.).
3. **Expose** in the Retool App via a **SQL query** on Retool DB: `SELECT supplier_id, supplier_name, portal_base_url FROM deck_supplier_portal_config WHERE is_active = true`.

**Iframe note:** Many supplier sites send `X-Frame-Options: DENY` or CSP `frame-ancestors 'none'`, so the **page may not embed** the portal. Plan for:
- **Primary:** clickable link + optional “Open portal in new tab”; **try iframe** only if you confirm headers allow it.
- **Fallback:** show supplier logo + URL text + “Open website” button.

---

## Phase 2 — Product / UX spec (single page)

**In Retool:** one **App** with one main **Frame** (or multipage if you prefer). URL is Retool-hosted unless you embed the app elsewhere.

**Name (example):** “Supplier portal — submit BO” in the Retool app list.

**Layout (top → bottom):**

| Section | Behaviour |
|---------|-----------|
| **Title + short warning** | “Submits the approved BO to the supplier’s portal via Deck. Only for configured suppliers.” |
| **BO id** | Text input (or searchable BO picker if you have a typeahead API). Validate numeric / UUID to match Optiply `buy_orders.id`. |
| **Supplier** | `Select` / dropdown: only suppliers with `deck_supplier_portal_config.is_active = true` (and optionally `portal_base_url IS NOT NULL`). Label: `supplier_name`, value: `supplier_id`. |
| **Portal preview** | On supplier change: show `portal_base_url` — **link** + optional **iframe** (see Phase 1). |
| **Resolved context** | After BO id + supplier selected, show read-only chips: **customer / webshop** (from BO), **supplier name**, **line count** or **preview table** (from a lightweight “BO summary” API — avoids typos before submit). |
| **Submit** | Primary button: “Submit to supplier portal”. Disabled until BO id + supplier valid and summary loaded without error. |
| **Job status** | After submit: show `deck_job` id, status (`connecting` → `adding_items` → `completed` / `needs_review` / `failed`), link to logs/Retool if applicable. **Poll** every 2–5 s until terminal state. |
| **Results** | When terminal: table of per-line Deck results (stock, price vs expected, added to cart) from stored `deck_jobs.results`. |

**Edge cases:** Wrong supplier for BO (BO’s supplier ≠ selected) → block submit with clear error. BO not approved → block or warn per policy.

---

## Phase 3 — Data queries (Retool-first)

Prefer **Retool queries** tied to resources; add a custom REST API only if you must centralize logic outside Retool.

| Query name (suggested) | Type | Purpose |
|------------------------|------|---------|
| `loadDeckSuppliers` | SQL → Retool DB | Rows for dropdown: `supplier_id`, `supplier_name`, `portal_base_url` where `is_active`. |
| `loadBoSummary` | SQL → Optiply DB (or REST) | Inputs: `bo_id`, `supplier_id`. Returns BO header + line preview + **`customer_id`** / `webshop_id` for the workflow. Include a check that the BO’s supplier matches `supplier_id`; return no rows or a flag if mismatch. |
| `loadDeckJobById` | SQL → Retool DB | `SELECT * FROM deck_jobs WHERE id = {{ ... }}` for polling after submit. |
| **Run Workflow A** | Workflow / manual trigger | Inputs: `bo_id`, `supplier_id`, `customer_id` from form + summary query — same as [WORKFLOW_A](./retool-blocks/WORKFLOW_A_deck_submit_order.md). |

**Optional later:** If you build a **first-party Optiply Admin** (non-Retool), reuse the same SQL/API contracts as these queries.

---

## Phase 4 — Retool App: drag-and-drop build steps

Build everything from the **Components** panel and **Queries** in the bottom panel. No hand-written SPA required.

### 4.1 Canvas layout (top → bottom)

1. **Text** — title + one-line warning (static copy).
2. **Text Input** — label “Buy order id”; bind **default value** or read from `{{ textInputBoId.value }}` in queries.
3. **Select** — label “Supplier”; **Data source**: `{{ loadDeckSuppliers.data }}` (or map to `{ label: supplier_name, value: supplier_id }` in a **Transformer** / **JavaScript** query if needed).
4. **Link** or **Button** (link style) — “Open supplier portal”; **URL**: `{{ selectSupplier.selectedItem?.portal_base_url }}` or lookup URL from selected row (see below).
5. **IFrame** (optional) — **URL** same as portal; hide or show a **Text** “Embedding blocked” fallback when the iframe fails (common for supplier sites).
6. **Table** — **Data**: `{{ loadBoSummary.data }}` (or line rows only). Set query to run **When inputs change** or on a **Refresh** button.
7. **Button** — “Submit to supplier portal”.
8. **Text** / **JSON** / **Table** — job `status`, `error_message`, and **results** from `loadDeckJobById`.

### 4.2 Bindings that matter

- **Selected supplier row:** If Select only stores `supplier_id`, add a **JavaScript** query or **Transformer**: find the row in `loadDeckSuppliers.data` where `supplier_id === selectSupplier.value` and expose `portal_base_url` for the Link and IFrame.
- **Run workflow on submit:** Button **Event handler** → **Control query** → choose **Run workflow** (or your Workflow resource’s “Trigger workflow” action) with parameters:
  - `bo_id`: `{{ textInputBoId.value }}`
  - `supplier_id`: `{{ selectSupplier.value }}`
  - `customer_id`: `{{ loadBoSummary.data[0].customer_id }}` (adjust path to your summary query shape)
- **Disable submit** until: BO id non-empty, supplier selected, summary query succeeded (e.g. `{{ loadBoSummary.data?.length > 0 }}` and no mismatch). Use Button **Disabled** field with `{{ ... }}`.

### 4.3 BO summary refresh

- Trigger `loadBoSummary` **manually** (button “Load / validate BO”) to avoid hammering the DB on every keystroke, **or** use **debounced** run if Retool version supports it.
- Pass SQL bindings: `:bo_id` ← `textInputBoId.value`, `:supplier_id` ← `selectSupplier.value`.

### 4.4 Polling job status

After the workflow returns (or you store **last inserted** `deck_job` id via a small follow-up query):

- Set **temporary state** (Retool **State** / **variable**) `deckJobId` from workflow return or from `insert_deck_job` if you expose it through a **Retool Workflow return value** / secondary query `SELECT id FROM deck_jobs WHERE bo_id = ... ORDER BY created_at DESC LIMIT 1`.
- Query `loadDeckJobById` with **Run behavior**: **Periodically** every 3–5 s, **Only when** `{{ deckJobId }}` is set and status not terminal (`completed`, `needs_review`, `failed`). In Retool 3.x patterns vary: you may use a **Poll** interval on the query or a **JS interval** in a module — use whatever your workspace already uses for live status.

### 4.5 Results table

- Bind a **Table** to `{{ loadDeckJobById.data.results.items }}` if `results` is the raw Deck `output` object; if nested differently, add a **JavaScript** query to normalize columns (`sku`, `status`, `price`, `price_is`, `added_to_cart`).

### 4.6 If you later replace Retool with Optiply Admin

Keep the **same user flow**; reimplement Phases 3–4 as real routes and components — the **workflow and DB** stay the source of truth.

---

## Phase 5 — Wiring to Deck (Workflow A)

Ensure the **manual workflow** (not webhook trigger) receives:

| Input | Source |
|-------|--------|
| `bo_id` | From admin submit (validated) |
| `supplier_id` | From dropdown |
| `customer_id` | From server-derived BO summary |

Flow matches [WORKFLOW_A_deck_submit_order.md](./retool-blocks/WORKFLOW_A_deck_submit_order.md): fetch lines → config → SKU mappings → transform → check in-flight → insert job → EnsureConnection → update `job_guid`.

**Add** after `check_in_flight_jobs`: **if count > 0, abort** with user-visible error (see review item #9).

---

## Phase 6 — Security & ops

- **No Deck secrets** in the browser; only server-side or Retool secrets.
- **Audit log:** who submitted which `bo_id` + `supplier_id` + timestamp + `deck_job_id`.
- **Rate limit** submit per BO / per supplier to prevent double cart loads.
- **Support playbook:** link from page to internal doc for `ACTIVE_CONNECTION_EXISTS`, MFA, timeout workflow C.

---

## Phase 7 — QA checklist

- [ ] Dropdown only shows active suppliers with URLs (if required).
- [ ] Changing supplier updates preview link/iframe immediately.
- [ ] Mismatched BO vs supplier blocked with clear message.
- [ ] Successful path: job reaches `completed` or `needs_review`, results visible.
- [ ] Failed Deck error surfaces `error_message` from `deck_jobs`.
- [ ] Polling stops on terminal state; query **Only when** / interval disabled so it does not run forever.

---

## Quick reference: minimal field mapping

| UI field | Workflow / DB |
|----------|----------------|
| BO id | `startTrigger.bo_id` → `fetch_bo_line_items_optiply` |
| Supplier dropdown value | `startTrigger.supplier_id` → `fetch_supplier_portal_config` |
| Website shown | `portal_base_url` from same config row (new column) |
| Customer id | From BO summary query row — passed into **Run workflow** with `bo_id` and `supplier_id` |

---

## Related files in this repo

- [context-and-implementation.md](./context-and-implementation.md) — Deck behaviour overview  
- [tech-plan-retool.md](./tech-plan-retool.md) — state machine, `deck_jobs`  
- [retool-blocks/README.md](./retool-blocks/README.md) — SQL/JS block inventory  
- [sample_data_hairaction_deck.sql](./retool-blocks/sample_data_hairaction_deck.sql) — example config rows  

**Default path:** implement entirely as a **Retool App** (drag-and-drop) + existing **Retool Workflows** + **SQL resources**. A future **Optiply Admin** page would mirror the same queries and workflow inputs.

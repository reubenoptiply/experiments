# Review: `deck-submit-order.json` (first version)

## Critical

### 1. `insert_deck_job` uses the wrong database resource

The block is configured with **`Optiply_ProductionDB`**, but `deck_jobs` lives in **Retool DB** (same resource as `fetch_supplier_portal_config`, `check_in_flight_jobs`, `update_deck_job` — UUID `01ebedd9-f35e-425f-9c3f-5429f9cfa4fe`).

**Fix:** Point `insert_deck_job` at **Retool DB**, not Optiply. Otherwise the insert either fails (table missing) or writes to the wrong place.

---

### 2. Hardcoded credentials in `EnsureConnection` REST block

The request **body** contains a real **email, password, and `source_guid`**. Headers contain **`x-deck-client-id`** and **`x-deck-secret`**.

- **Rotate** all of these credentials (they are exposed in this file).
- Move Deck id/secret to **Retool Secrets** / env.
- Move portal username/password to **Secrets** (or per-customer store later).
- Set REST **body** to `{{ build_ensure_connection_body.data.body }}` (or equivalent) instead of a static JSON string.

---

### 3. `build_ensure_connection_body` is not used by `EnsureConnection`

The REST block uses a **hardcoded** JSON body, so **`build_ensure_connection_body` is dead code** for the API call. Even if you fix the JS, it won’t affect Deck until the REST block references its output.

**Fix:** REST body = dynamic from `build_ensure_connection_body`, and fix the JS so `username` / `password` come from secrets (not undefined `source_guid` / `username` / `password` args — today the function still uses `fetch_supplier_portal_config.data[0].source_guid` inside `input` but `username`/`password` end up `''` because the outer call passes undefined).

---

## Critical — SQL / data

### 4. `fetch_supplier_portal_config` — extra `)` (syntax error)

```sql
... supplier_id = CAST({{ startTrigger.supplier_id }} AS TEXT));
```

There is an **extra closing parenthesis** before the semicolon. Should end with `AS TEXT)` only (one `)` before `;`).

---

### 5. `fetch_bo_line_items_optiply` — hardcoded BO id

```sql
AND bo.id = 2559945;
```

**Fix:** Use `{{ startTrigger.bo_id }}` (or your manual trigger’s run input) so each run targets the selected buy order.

---

### 6. `fetch_bo_line_items_optiply` — `supplier_products` join

Current join is only `JOIN supplier_products sp ON bo.seller_id = sp.supplier_id`, which can return **many rows per line** (all products for that supplier), breaking `transform_bo_to_deck_items` (duplicate SKUs / wrong quantities).

**Fix:** Join each line to one product, e.g. `AND sp.id = bol.supplier_product_id` (or whatever column links `buy_order_lines` → `supplier_products` in your schema).

---

### 7. `insert_deck_job` — `items` JSON binding

```sql
CAST({{ transform_bo_to_deck_items.items }} AS JSONB)
```

In Retool, query results are usually under **`.data`**. This should be something like:

- `{{ JSON.stringify(transform_bo_to_deck_items.data.items) }}`  
  or the pattern your Retool version expects for JSONB parameters.

Using `.items` on the block name often resolves incorrectly and can produce invalid SQL or `NULL`.

---

## High — trigger & control flow

### 8. Trigger type: **Webhook** vs **Manual**

`startTrigger` is **`blockType: "webhook"`**. The submit-order flow is meant to be started from the **Admin Panel** with `bo_id`, `customer_id`, `supplier_id`.

**Improvement:** Use a **Manual / Run workflow** trigger (or whatever Retool calls it) and define **workflow inputs** for those three fields. If you keep Webhook, the app must POST to the workflow URL with the same shape — still document and align `startTrigger.data` with `parse` expectations.

### 9. `check_in_flight_jobs` does not block the flow

The chain always continues: `check_in_flight_jobs` → `insert_deck_job`. If rows are returned, you still insert and call EnsureConnection.

**Fix:** Add a **conditional** after `check_in_flight_jobs`: if `data.length > 0`, **stop** or return an error; else continue to `insert_deck_job`.

---

## Medium

### 10. `update_deck_job` parameters

Uses `:job_guid`, `:id`, etc. Ensure they are **bound** in Retool, e.g.:

- `:id` ← `insert_deck_job.data.id` (or `[0].id`)
- `:job_guid` ← `EnsureConnection` response `job_guid` (exact path depends on REST response shape)

If unbound, `COALESCE(CAST(NULL AS TEXT), job_guid)` may leave `job_guid` unchanged — webhook correlation breaks.

### 11. `transform_bo_to_deck_items`

Only passes two arguments; **`currencySymbol`** is omitted (defaults to `€` — OK). Confirm `fetch_bo_line_items_optiply.data` / `fetch_sku_mappings.data` are the correct shapes in workflow context (array vs nested).

### 12. `isEnabled: false`

Workflow won’t run until enabled.

### 13. Production naming

`Optiply_ProductionDB` for read-only BO lines is a conscious choice; ensure you’re not hitting production for pilot tests if you intended sandbox.

### 14. Git / exports

Avoid committing JSON exports that contain secrets. Add to `.gitignore` or strip credentials before commit.

---

## Quick checklist

| Priority | Item |
|----------|------|
| P0 | Point `insert_deck_job` at **Retool DB** |
| P0 | Remove hardcoded Deck + portal credentials; use secrets; REST body from `build_ensure_connection_body` |
| P0 | Fix `fetch_supplier_portal_config` extra `)` |
| P0 | Replace hardcoded `bo.id = 2559945` with `{{ startTrigger.bo_id }}` |
| P0 | Fix `insert_deck_job` `items` → `transform_bo_to_deck_items.data.items` (or correct Retool JSON pattern) |
| P1 | Fix `supplier_products` join so one row per line |
| P1 | Branch after `check_in_flight_jobs` to skip insert when in-flight |
| P2 | Manual trigger + input schema; enable workflow; verify `update_deck_job` bindings |

---

## What looks good

- Linear order matches the design: BO lines → config → SKU mappings → transform → in-flight check → insert job → build body → EnsureConnection → update `job_guid`.
- `fetch_sku_mappings` / `check_in_flight_jobs` use `{{ startTrigger.supplier_id }}` (aside from the extra `)` in config).
- `update_deck_job` SQL structure matches the canonical multi-column update pattern.
- Deck headers on EnsureConnection use **`x-deck-client-id`** / **`x-deck-secret`** (correct names; values must come from secrets, not the file).

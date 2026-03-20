# Review: `deck-webhook-receiver.json` (first version)

## Critical — security

1. **Deck credentials are hardcoded** in the REST blocks `AddItemsToCart` and `CloseConnection` (headers `client_id` / `client_secret` with UUID values).  
   - **Do:** Use Retool **Secrets** or **Environment variables** and reference them in headers (never commit real values).  
   - **Do:** **Rotate** those Deck credentials with Deck — they are now exposed in this repo/export.

2. **Wrong header names for Deck (likely)**  
   Deck’s docs specify **`x-deck-client-id`** and **`x-deck-secret`**, not `client_id` / `client_secret`. Confirm with Deck; if the API only accepts the `x-deck-*` headers, requests will fail or behave unexpectedly.

---

## Critical — SQL / data bugs

3. **`get_deck_job_by_guid` query is invalid**  
   Current fragment:
   ```sql
   WHERE job_guid = CAST(parse_webhook_dispatch.job_guid AS TEXT)
   ```
   `parse_webhook_dispatch` is not a SQL table. Retool will not resolve that.  
   **Fix:** Use a template, e.g.  
   `WHERE job_guid = {{ parse_webhook_dispatch.data.job_guid }}`  
   (or a named query parameter bound to that expression).

4. **`update_deck_job` (EnsureConnection path) — missing comma**  
   In the export, the `SET` clause has:
   ```sql
   status = COALESCE(...),
   updated_at = now()
   ```
   but between `status` and `updated_at` the comma is **missing** after the `status` line (you have `status ... \n  updated_at` without `,`). That is a **SQL syntax error** and the block will fail.  
   **Fix:** Add a comma after the `status` line (match the canonical `update_deck_job.sql` in `retool-blocks/`).

---

## Critical — workflow graph / logic

5. **`MfaRequired` branch is not connected**  
   Conditional port `3` (`MfaRequired`) has no downstream block. Deck could send this webhook; nothing will run.  
   **Fix:** Add the same pattern as `Error` (e.g. `get_deck_job` already ran — then `UPDATE deck_jobs SET status = 'failed', error_message = '...'` + optional Slack).

6. **No handling when `get_deck_job_by_guid` returns 0 rows**  
   If `job_guid` doesn’t match (timing bug, manual DB change, wrong env), later blocks still run and updates use empty `id` → failures or wrong rows.  
   **Improvement:** After `get_deck_job_by_guid`, add a **branch** on `data.length` / row exists; if false, log + return (or Slack alert) and **do not** run `action_branch` updates.

---

## High — JS block inputs (likely broken unless you bound them in UI)

7. **`build_add_items_to_cart_body`**  
   Code ends with `return buildAddItemsToCartBody(access_token, items);` but `access_token` and `items` must be **explicit query inputs** in Retool, e.g.:  
   - `access_token` ← `parse_webhook_dispatch.data.access_token`  
   - `items` ← `get_deck_job_by_guid.data.items` (or `get_deck_job_by_guid.data[0].items` depending on shape)

8. **`build_close_connection_body`**  
   Same issue: `access_token` must be bound to **`get_deck_job_by_guid.data.access_token`** (or first row), not an implicit global.

9. **`compute_add_items_status`**  
   `addItemsOutput` must be bound to **`parse_webhook_dispatch.data.output`** (full `output` object from the AddItemsToCart webhook).

The JSON export does not show `importedQueryInputs` for these blocks; if they’re empty in Retool, these blocks will throw or return wrong data.

---

## Medium — behaviour & resilience

10. **REST failures**  
    If `AddItemsToCart` or `CloseConnection` returns 4xx/5xx, there is no **failure path** (retry, mark job `failed`, Slack). Consider an **on failure** edge or a try/catch pattern Retool supports.

11. **AddItemsToCart webhook `output.success === false`**  
    Deck can return a webhook with `success: false` and a message. `compute_add_items_status` may still set `completed` if `items` is empty. Consider treating `output.success === false` as `failed` or `needs_review`.

12. **`Unknown` action**  
    If `webhook_code` doesn’t match, `action` is `Unknown` and no branch runs — OK, but you may want logging/Slack.

13. **Workflow disabled**  
    `"isEnabled": false` — webhooks won’t run in production until enabled.

14. **No Slack / notifications**  
    Spec called for alerts on completion and errors; not present yet.

15. **`parse_webhook_dispatch`**  
    Uses `startTrigger.data` — correct if your webhook payload lives there; if Deck sends nested body, use `startTrigger.body` (verify with one real webhook in Retool’s run log).

---

## Low / housekeeping

16. **Duplicate responsibility**  
    `action_branch` has both UI conditions **and** a script with `executePathAtMostOnce` — ensure they stay in sync (same four actions).

17. **`update_error` SQL**  
    Comment says “timeout” but this block is for Deck `Error` webhook — update comment for clarity.

18. **Sandbox vs live**  
    URL is `https://live.deck.co/...` — use sandbox for testing if that’s your process.

19. **Git**  
    Add `deck-webhook-receiver.json` to `.gitignore` if it may contain secrets, or strip secrets before commit.

---

## What’s working well

- Overall shape matches the design: parse → lookup job → branch → EnsureConnection chain (update token → build body → POST AddItems → update job_guid) and AddItemsToCart chain (compute status → update results → CloseConnection).  
- Error path goes to `update_error` after the shared `get_deck_job_by_guid` (so `id` is available if the row exists).  
- Separate SQL blocks for different updates (`update_deck_job`, `update_deck_job_add_items`, `update_deck_job_results`) are easier to reason about than one mega-query.

---

## Quick fix checklist

| Priority | Item |
|----------|------|
| P0 | Rotate Deck credentials; remove from JSON; use secrets + correct headers (`x-deck-*` per Deck docs) |
| P0 | Fix `get_deck_job_by_guid` WHERE clause (template / param, not `parse_webhook_dispatch` in SQL) |
| P0 | Fix `update_deck_job` missing comma before `updated_at` |
| P0 | Bind JS inputs: `access_token`, `items`, `addItemsOutput` |
| P1 | Wire **MfaRequired** branch |
| P1 | Handle empty `get_deck_job_by_guid` result |
| P2 | Failure handling on REST blocks; `output.success === false`; Slack |
| P2 | Enable workflow when ready |

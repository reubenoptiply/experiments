# Deck Supplier Portal — Workflow flowcharts

Detailed flowcharts and block-by-block instructions are in **one markdown per workflow**:

| Workflow | File | Trigger | Deck API called |
|----------|------|--------|------------------|
| **A** | [WORKFLOW_A_deck_submit_order.md](./WORKFLOW_A_deck_submit_order.md) | Manual / Run from app | **EnsureConnection** only |
| **B** | [WORKFLOW_B_deck_webhook_receiver.md](./WORKFLOW_B_deck_webhook_receiver.md) | Webhook (Deck POST) | **AddItemsToCart**, **CloseConnection** |
| **C** | [WORKFLOW_C_deck_job_timeout_check.md](./WORKFLOW_C_deck_job_timeout_check.md) | Schedule | None |

---

## Where each Deck endpoint is called

| Deck endpoint | Workflow | When / which block |
|---------------|----------|--------------------|
| **EnsureConnection** | **A** (deck-submit-order) | After insert_deck_job and build_ensure_connection_body — **HTTP POST** to `.../api/v1/jobs/submit` with `job_code: "EnsureConnection"`. |
| **AddItemsToCart** | **B** (deck-webhook-receiver) | In the **EnsureConnection** branch, after we receive the webhook with `access_token`. Block: **HTTP POST Deck — AddItemsToCart** (build body from job’s `items` + token, then POST same URL with `job_code: "AddItemsToCart"`). |
| **CloseConnection** | **B** (deck-webhook-receiver) | In the **AddItemsToCart** branch, after we store results and status. Block: **HTTP POST Deck — CloseConnection** (body with `job_code: "CloseConnection"` and `access_token` from the job row). |

So: **AddItemsToCart** is called only in **Workflow B**, in the branch that runs when Deck sends the **EnsureConnection** webhook (success). We do not call AddItemsToCart from Workflow A.

**Webhook handling:** Deck sends **one HTTP POST per event**. Each POST starts a **new run** of Workflow B (no queue inside the workflow). First run gets EnsureConnection → we call AddItemsToCart API; second run (later) gets AddItemsToCart → we call CloseConnection. Shared state is only the `deck_jobs` table. See [WORKFLOW_B_deck_webhook_receiver.md](./WORKFLOW_B_deck_webhook_receiver.md) § “How the webhook queue works”.

---

## Quick reference

- **Workflow A:** Trigger → fetch BO lines + config + SKU mappings → transform → check in-flight → insert_deck_job → build EnsureConnection body → **POST EnsureConnection** → update job_guid.
- **Workflow B:** Webhook → parse → **branch on action** → EnsureConnection path: get job → update (token) → build AddItems body → **POST AddItemsToCart** → update job_guid; AddItemsToCart path: get job → compute status → update (results) → build Close body → **POST CloseConnection** → notify.
- **Workflow C:** Schedule → stuck_jobs_timeout SQL → **loop** → mark_job_failed_timeout → optional Slack.

For full block names, bindings, and data flow, open the three workflow markdown files above.

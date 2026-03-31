# WWW26 — Supplier portal demo (Hairaction)

Implements the **Core Flows — WWW26 Demo App & Video** spec: Retool demo UI, Deck live flow to hairaction.nl, transactional email, and Loom narrative.

## Where everything lives

| Deliverable | Location |
|-------------|----------|
| Retool blocks (JS/SQL) + workflow guide | [retool-blocks/WORKFLOW_WWW26_Demo.md](../retool-blocks/WORKFLOW_WWW26_Demo.md) |
| Static HTML wireframes (copy into Retool HTML component or browser preview) | [reference/](./reference/) |

## Before recording

1. Confirm **SKUs** on hairaction.nl; update `LINE_ITEMS` / `PRODUCT_NAMES` in `www26_hardcoded_buy_order.js` and `www26_merge_stored_items_for_email.js` together.
2. Add **Deck screenshot** PNGs; see [reference/assets.md](./reference/assets.md).
3. Configure Retool secrets: Deck **live** URL, portal credentials, `WWW26_DEMO_NOTIFY_EMAIL`.

## Video script

Use the **Talking Points Script** section in the Traycer spec (0:00–1:55): pain → one click → agent → results → email → value proposition.

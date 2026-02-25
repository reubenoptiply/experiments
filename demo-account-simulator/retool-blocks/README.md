# Retool blocks (canonical)

Copy these files into your Retool Workflow. They form the **Creator** data path for the demo account simulator (Shop 1380).

**Order and dependencies**

1. **fetch_product_meta.sql** — Products for webshop 1380 (32 whitelisted IDs), including `supplier_id` and `supplier_uuid`. Run first (e.g. after trigger).
2. **fetch_daily_sales.sql** — Daily units sold per product (last 366 days). Run in parallel or after fetch_product_meta.
3. **simulate_stocks.py** — Python block. Inputs: `fetch_product_meta.data`, `fetch_daily_sales.data`. Output: `{ stocks, buy_orders, item_deliveries }`.
4. **soft_delete_stocks.sql** — Soft-delete existing stocks for shop 1380. Run after simulate_stocks.
5. **build_stocks_insert.js** — JS block. Input: `simulate_stocks.data.stocks`. Output: `{ record_set }`. Run after simulate_stocks.
6. **insert_stocks.sql** — SQL block; run after build_stocks_insert.

**BOs and receipt lines (API loops) — no stock re-simulation**

Stocks are already in the DB. To create only buy orders and receipt lines from existing data:

7. **fetch_stocks.sql** — Query existing stock history from DB (product_id, stock_date, on_hand) for webshop 1380, last 365 days. Run with fetch_product_meta and fetch_daily_sales.
8. **simulate_buy_orders_from_stocks.py** — Python block. Inputs: `fetch_product_meta.data`, `fetch_daily_sales.data`, `fetch_stocks.data`. Infers delivery events from stock increases (after accounting for sales) and back-calculates buy orders. Output: `{ buy_orders, item_deliveries }` only (no stocks). Run after the three fetches.
9. **build_buy_order_api_bodies.js** — JS block. Input: `simulate_buy_orders_from_stocks.data` (or `simulate_stocks.data` if you ever use the full simulation). Output: `buy_order_bodies`, `item_deliveries_meta`. Run after simulate_buy_orders_from_stocks.
10. **Retool Loop: POST buy orders** — Loop over `build_buy_order_api_bodies.data.buy_order_bodies`. Each iteration: **POST** `https://api.optiply.com/v1/buyOrders?accountId=1380`, header `Content-Type: application/vnd.api+json`, body = loop item. Delay ~200 ms between iterations. Name block e.g. `post_buy_orders_loop`.
11. **build_receipt_line_bodies.js** — JS block. Reads Loop responses (set `post_buy_orders_loop` to your Loop block name), extracts `buyOrderLineId`, outputs `receipt_line_bodies`. Run after the buy-orders Loop.
12. **Retool Loop: POST receipt lines** — Loop over `build_receipt_line_bodies.data.receipt_line_bodies`. **POST** each to `https://api.optiply.com/v1/receiptLines?accountId=1380`, same header.

**Patching `completed` on BOs**

After creating BOs, set `completed` (when the BO was closed) so past-due orders are marked delivered. Use **build_patch_completed_bodies.js** then a Loop that PATCHes each.

13. **build_patch_completed_bodies.js** — Input: list of created BOs **with ids** (e.g. `post_buy_orders_loop.data` from the create Loop, or GET buyOrders response). Optional: if your list has no ids (e.g. request bodies only), bind `bo_ids_in_order` to an array of BO ids in the same order. **Or** use **fetch_bo_data.data** (see below): the block accepts rows with `bo_id` and `bo_expected_delivery_date`, dedupes by `bo_id`, and skips future-dated BOs; ~80% on-time, ~20% late. Output: `patch_items` = `[{ id, body }]`.
14. **Retool Loop: PATCH buy orders** — Loop over `build_patch_completed_bodies.data.patch_items`. Each iteration: **PATCH** `https://api.optiply.com/v1/buyOrders/{{ item.id }}?accountId=1380`, header `Content-Type: application/vnd.api+json`, body = `item.body`. Delay between iterations as needed.

**When BOs already exist in DB: patch completed + create receipt lines from one query**

Use a single SQL block to load BO/BOL ids and dates, then drive both the patch-completed loop and the receipt-line (delivery) loop.

15. **fetch_bo_data.sql** — Query: `buy_orders` joined to `buy_order_lines` for webshop 1380, returning `bo_id`, `bol_id`, `placed`, `bo_expected_delivery_date`, `bol_expected_delivery_date`, `webshop_product_id`, `supplier_id`, `quantity`. Run this SQL block first.
16. **build_patch_completed_bodies** — Bind input to **fetch_bo_data.data**. Block dedupes by `bo_id`, skips future-dated BOs, builds `patch_items`. Then **Loop: PATCH buy orders** as above.
17. **build_receipt_line_bodies_from_bo_data.js** — Input: **fetch_bo_data.data**. Builds `receipt_line_bodies` (one per row: `buyOrderLineId` = `bol_id`, `occurred` = expected delivery date, `quantity` from row). No create responses needed. Run after fetch_bo_data.
18. **Retool Loop: POST receipt lines** — Loop over `build_receipt_line_bodies_from_bo_data.data.receipt_line_bodies`. **POST** each to `https://api.optiply.com/v1/receiptLines?accountId=1380`, header `Content-Type: application/vnd.api+json`, body = loop item.

**Block flow**

- **BO-only (stocks already inserted):** `fetch_product_meta` + `fetch_daily_sales` + `fetch_stocks` → `simulate_buy_orders_from_stocks` → `build_buy_order_api_bodies` → Loop (POST buyOrders) → `build_receipt_line_bodies` → Loop (POST receiptLines). Optionally then: **build_patch_completed_bodies** → Loop (PATCH buyOrders) to set `completed`.
- **BOs already in DB (patch + deliveries):** **fetch_bo_data** (SQL) → **build_patch_completed_bodies** (input = fetch_bo_data.data) → Loop (PATCH buyOrders); and **fetch_bo_data** → **build_receipt_line_bodies_from_bo_data** → Loop (POST receiptLines). You can run the PATCH loop and the receipt-line loop in parallel or one after the other.
- **Full Creator (stocks not yet inserted):** `fetch_product_meta` + `fetch_daily_sales` → `simulate_stocks` → stocks path (soft_delete_stocks → build_stocks_insert → insert_stocks) and/or same BO path using `simulate_stocks.data` (build_buy_order_api_bodies accepts either source).

If you only have request bodies (e.g. sample-data/bos-created.json) and no ids, run a **GET** buyOrders query for the account, then pass the response as the BO list (so each item has `id` and `expectedDeliveryDate`) or pass the array of ids as `bo_ids_in_order` in the same order as your request bodies.

Ensure `build_receipt_line_bodies` references your buy-orders Loop block correctly; adjust `getBuyOrderLineIdFromResponse` if the API response shape differs.

See [plan/README.md](../plan/README.md) and the [Retool Workflow Builder Guide](../plan/Retool_Workflow_Builder_Guide_—_Creator_&_Maintainer.md) for full workflow setup.

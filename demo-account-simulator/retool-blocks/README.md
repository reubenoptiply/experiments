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

**Assembly orders (Phase 1 + Phase 2: create, receipt lines, complete / in-transit)**

Phase 1 creates assembly orders from stock history; Phase 2 adds receipt lines (from BO/BOL SQL data) and marks past-due orders as completed (future-dated stay in transit).

19. **simulate_assembly_orders_from_stocks.py** — Python block. Inputs: `fetch_product_meta.data`, `fetch_daily_sales.data`, `fetch_stocks.data`. Assembly products only (hardcoded IDs). Output: `{ assembly_orders, item_deliveries }`. Run with the same fetches as the BO-from-stocks path.
20. **build_assembly_order_api_bodies.js** — JS block. Input: `simulate_assembly_orders_from_stocks.data`. Output: `assembly_order_bodies`, `item_deliveries_meta`. Run after simulate_assembly_orders_from_stocks.
21. **Retool Loop: POST assembly orders** — Loop over `build_assembly_order_api_bodies.data.assembly_order_bodies`. **POST** each to `https://api.optiply.com/v1/buyOrders?accountId=1380`, same header. Name block e.g. `post_assembly_orders_loop`.
22. **fetch_bo_data_assembly.sql** — SQL block. Returns BO/BOL rows for assembly orders only. Run after assembly orders exist in DB (e.g. after the POST assembly orders Loop, or when they were created earlier).
23. **build_assembly_receipt_line_bodies.js** — JS block (Phase 2). Input: **fetch_bo_data_assembly.data** (or **fetch_bo_data.data**). Builds `receipt_line_bodies` from each row: `buyOrderLineId` = `bol_id`, `occurred` = expected delivery date, `quantity`. No create responses needed. Run after fetch_bo_data_assembly.
24. **Retool Loop: POST receipt lines (assembly)** — Loop over `build_assembly_receipt_line_bodies.data.receipt_line_bodies`. **POST** each to `https://api.optiply.com/v1/receiptLines?accountId=1380`, same header.
25. **build_patch_completed_from_bo_data.js** — Input: **fetch_bo_data_assembly.data** (or **fetch_bo_data.data**). Dedupes by bo_id, builds PATCH bodies with **completed = expected_delivery_date** for every BO (no skip, no random late). **Loop: PATCH buy orders** over `build_patch_completed_from_bo_data.data.patch_items` (PATCH each `item.id` with `item.body`).
26. **build_active_assembly_order_bodies.js** — Builds a few (e.g. 3) assembly order POST bodies with **expected_delivery_date in the future** and no completed (active orders). Input: **fetch_product_meta.data** (must include assembly product IDs 29177521, 29177522, 29177523 — extend your product query if needed). Output: `active_assembly_order_bodies`. **Loop: POST** each to create active orders; do not patch completed on these.

**Assembly BOs already in DB:** Use **fetch_bo_data_assembly.sql** → **build_assembly_receipt_line_bodies** → Loop (POST receipt lines); then **fetch_bo_data_assembly** → **build_patch_completed_from_bo_data** → Loop (PATCH buy orders so completed = expected_delivery_date). Then **build_active_assembly_order_bodies** → Loop (POST) to create a few active (future-dated) orders. Requires `buy_orders.assembly` column.

**Block flow**

- **BO-only (stocks already inserted):** `fetch_product_meta` + `fetch_daily_sales` + `fetch_stocks` → `simulate_buy_orders_from_stocks` → `build_buy_order_api_bodies` → Loop (POST buyOrders) → `build_receipt_line_bodies` → Loop (POST receiptLines). Optionally then: **build_patch_completed_bodies** → Loop (PATCH buyOrders) to set `completed`.
- **Assembly (Phase 1 + 2):** same fetches + `simulate_assembly_orders_from_stocks` → `build_assembly_order_api_bodies` → Loop (POST assembly orders) → **fetch_bo_data_assembly** → `build_assembly_receipt_line_bodies` → Loop (POST receipt lines) → **build_patch_completed_from_bo_data** (input = fetch_bo_data_assembly.data) → Loop (PATCH buyOrders; completed = expected_delivery_date). Then **build_active_assembly_order_bodies** → Loop (POST) to create a few active (future-dated) orders with no completed.
- **BOs already in DB (patch + deliveries):** **fetch_bo_data** (SQL) → **build_patch_completed_bodies** (input = fetch_bo_data.data) → Loop (PATCH buyOrders); and **fetch_bo_data** → **build_receipt_line_bodies_from_bo_data** → Loop (POST receiptLines). You can run the PATCH loop and the receipt-line loop in parallel or one after the other. For assembly only: use **fetch_bo_data_assembly.sql**.
- **Full Creator (stocks not yet inserted):** `fetch_product_meta` + `fetch_daily_sales` → `simulate_stocks` → stocks path (soft_delete_stocks → build_stocks_insert → insert_stocks) and/or same BO path using `simulate_stocks.data` (build_buy_order_api_bodies accepts either source).

If you only have request bodies (e.g. sample-data/bos-created.json) and no ids, run a **GET** buyOrders query for the account, then pass the response as the BO list (so each item has `id` and `expectedDeliveryDate`) or pass the array of ids as `bo_ids_in_order` in the same order as your request bodies.

Ensure `build_receipt_line_bodies` references your buy-orders Loop block name; adjust `getBuyOrderLineIdFromResponse` if the API response shape differs. For assembly, `build_assembly_receipt_line_bodies` uses **fetch_bo_data_assembly.data** (or **fetch_bo_data.data**) — no Loop binding needed.

See [plan/README.md](../plan/README.md) and the [Retool Workflow Builder Guide](../plan/Retool_Workflow_Builder_Guide_—_Creator_&_Maintainer.md) for full workflow setup.

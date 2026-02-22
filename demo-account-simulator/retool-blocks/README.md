# Retool blocks (canonical)

Copy these files into your Retool Workflow. They form the **Creator** data path for the demo account simulator (Shop 1380).

**Order and dependencies**

1. **fetch_product_meta.sql** — Products for webshop 1380 (32 whitelisted IDs), including `supplier_id` and `supplier_uuid`. Run first (e.g. after trigger).
2. **fetch_daily_sales.sql** — Daily units sold per product (last 366 days). Run in parallel or after fetch_product_meta.
3. **simulate_stocks.py** — Python block. Inputs: `fetch_product_meta.data`, `fetch_daily_sales.data`. Output: `{ stocks, buy_orders, item_deliveries }`.
4. **soft_delete_stocks.sql** — Soft-delete existing stocks for shop 1380. Run after simulate_stocks.
5. **build_stocks_insert.js** — JS block. Input: `simulate_stocks.data.stocks`. Output: `{ record_set }`. Run after simulate_stocks.
6. **insert_stocks.sql** — SQL block; run after build_stocks_insert.

**BOs and receipt lines (API loops)**

7. **build_buy_order_api_bodies.js** — JS block. Input: `simulate_stocks.data`. Output: `buy_order_bodies` (array of JSON:API bodies for POST buyOrders), `item_deliveries_meta` (for receipt lines). Run after simulate_stocks.
8. **Retool Loop: POST buy orders** — In Retool, add a **Loop** block that runs after `build_buy_order_api_bodies`. Loop over `build_buy_order_api_bodies.data.buy_order_bodies`. Each iteration: **POST** `https://api.optiply.com/v1/buyOrders?accountId=1380` (or your accountId), header `Content-Type: application/vnd.api+json`, body = current loop item. Use a small delay (e.g. 200 ms) between iterations to respect rate limits. Name this block e.g. `post_buy_orders_loop`.
9. **build_receipt_line_bodies.js** — JS block. Inputs: `build_buy_order_api_bodies.data.item_deliveries_meta` (or `simulate_stocks.data.item_deliveries`), and the **Loop block’s output** (array of POST responses). In the block code, set `post_buy_orders_loop` to your actual Loop block name so it can read the responses and extract `buyOrderLineId` from each. Output: `receipt_line_bodies` (array of JSON:API bodies for POST receiptLines). Run after the buy-orders Loop.
10. **Retool Loop: POST receipt lines** — Add a second **Loop** block. Loop over `build_receipt_line_bodies.data.receipt_line_bodies`. Each iteration: **POST** `https://api.optiply.com/v1/receiptLines?accountId=1380`, header `Content-Type: application/vnd.api+json`, body = current loop item. Delay between iterations as needed.

**Block flow**

- Stocks path: `simulate_stocks` → `soft_delete_stocks` → `build_stocks_insert` → `insert_stocks`.
- BO path: `simulate_stocks` → `build_buy_order_api_bodies` → Loop (POST buyOrders) → `build_receipt_line_bodies` → Loop (POST receiptLines).

You can run the BO path only when backfilling buy orders and deliveries (e.g. after initial sales/stocks import). Ensure `build_receipt_line_bodies` uses the correct reference to your buy-orders Loop block so it can read responses and extract line IDs; if your API response shape differs, adjust `getBuyOrderLineIdFromResponse` in that block.

See [plan/README.md](../plan/README.md) and the [Retool Workflow Builder Guide](../plan/Retool_Workflow_Builder_Guide_—_Creator_&_Maintainer.md) for full workflow setup.

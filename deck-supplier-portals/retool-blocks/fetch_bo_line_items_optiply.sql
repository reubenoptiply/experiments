-- Optiply DB resource: fetch line items for given buy orders (for Deck item transformation).
-- Bind :bo_ids to an array of buy order IDs, e.g. {{ [ 'id1', 'id2' ] }} or from your app state.
-- Returns one row per line: bo_id, line quantity, unit_price, product sku and supplier_sku for mapping.
-- Adjust table/column names to match your Optiply schema (buy_orders, buy_order_lines, products).

SELECT
  bol.buy_order_id AS bo_id,
  bol.id AS line_id,
  bol.product_id,
  bol.quantity,
  bol.unit_price,
  p.sku AS optiply_sku,
  COALESCE(p.supplier_sku, p.sku) AS supplier_sku,
  p.name AS product_name
FROM buy_order_lines bol
JOIN products p ON p.id = bol.product_id
JOIN buy_orders bo ON bo.id = bol.buy_order_id
WHERE bo.status = 'approved'
  AND bol.buy_order_id::text = ANY(CAST(COALESCE(:bo_ids, '{}') AS TEXT[]));

-- Block: fetch_bo_data_assembly
-- Same as fetch_bo_data but only assembly orders (bo.assembly = true).
-- Use for: (1) patch completed on assembly BOs only, (2) receipt lines for assembly order lines.
-- Requires buy_orders.assembly column. One row per buy_order_line; dedupe by bo_id for patch.
SELECT
  bo.id AS bo_id,
  bol.id AS bol_id,
  bo.placed,
  bo.expected_delivery_date AS bo_expected_delivery_date,
  bol.expected_delivery_date AS bol_expected_delivery_date,
  bol.product_id AS webshop_product_id,
  bo.seller_id AS supplier_id,
  bol.quantity
FROM buy_orders bo
JOIN buy_order_lines bol ON bo.id = bol.buy_order_id
WHERE bo.webshop_id = 1380
  AND bo.assembly = true
  AND bo.deleted_at IS NULL
  AND bol.deleted_at IS NULL;

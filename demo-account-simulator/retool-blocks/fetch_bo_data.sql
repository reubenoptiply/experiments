-- Block: fetch_bo_data
-- BO and BOL ids + dates for webshop 1380. Use for: (1) patch completed bodies, (2) receipt line (delivery) bodies.
-- One row per buy_order_line. Dedupe by bo_id when building patch items; use each row for one receipt line.
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
  AND bo.deleted_at IS NULL
  AND bol.deleted_at IS NULL;

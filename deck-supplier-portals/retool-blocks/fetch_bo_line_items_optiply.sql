-- Optiply DB: buy order lines for one BO (for Deck item transformation).
-- Uses Retool template {{ startTrigger.bo_id }} in the query (no colon — value is inlined by Retool).
-- To scope by webshop/seller, add: AND bo.webshop_id = {{ startTrigger.webshop_id }} AND bo.seller_id = {{ startTrigger.seller_id }}
SELECT
  bo.id AS bo_id,
  bol.id AS line_id,
  bo.seller_id AS supplier_id,
  s.name AS s_name,
  sp.name AS sp_name,
  sp.sku,
  sp.ean_code,
  bol.quantity,
  bol.subtotal_value,
  (bol.subtotal_value / NULLIF(bol.quantity, 0)) AS unit_price,
  sp.sku AS optiply_sku,
  sp.sku AS supplier_sku,
  sp.name AS product_name
FROM buy_orders bo
JOIN buy_order_lines bol ON bo.id = bol.buy_order_id
JOIN supplier_products sp ON bo.seller_id = sp.supplier_id AND sp.id = bol.supplier_product_id
JOIN suppliers s ON bo.seller_id = s.id
WHERE bo.deleted_at IS NULL
  AND bol.deleted_at IS NULL
  AND bo.id = {{ startTrigger.bo_id }};

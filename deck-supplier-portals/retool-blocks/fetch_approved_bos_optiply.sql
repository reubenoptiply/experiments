-- Optiply DB resource: fetch approved buy orders not yet submitted to Deck.
-- Exclude BOs already in deck_jobs (not failed) by filtering in the app using submitted_bo_ids, or join if both in same DB.
-- Adjust table/column names to match your Optiply Postgres schema (e.g. buy_orders, buy_order_lines, products, suppliers).

SELECT
  bo.id AS bo_id,
  bo.reference AS bo_reference,
  bo.supplier_id,
  bo.customer_id,
  s.name AS supplier_name,
  bo.created_at
FROM buy_orders bo
JOIN suppliers s ON s.id = bo.supplier_id
WHERE bo.status = 'approved'
ORDER BY bo.created_at DESC;

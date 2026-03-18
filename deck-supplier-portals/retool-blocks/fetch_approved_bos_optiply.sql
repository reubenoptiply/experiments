-- Optiply DB resource: fetch approved buy orders not yet submitted to Deck.
-- Exclude BOs that are already in deck_jobs with status not in (failed) so we don't resubmit.
-- Bind :bo_ids_already_submitted to the result of a Retool DB query that returns
--   SELECT array_agg(bo_id) FROM deck_jobs, jsonb_array_elements_text(bo_ids) AS bo_id WHERE status NOT IN ('failed')
-- or run this query without exclusion for a first pass and filter in the app.
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
  -- Exclude BOs already in-flight or completed in deck_jobs (bind from Retool DB query if needed):
  -- AND bo.id::text NOT IN (SELECT jsonb_array_elements_text(dj.bo_ids) FROM deck_jobs dj WHERE dj.status NOT IN ('failed'))
ORDER BY bo.created_at DESC;

-- Block B: fetch_daily_sales
-- Aggregates sell_order_lines to daily units per product (last 365 days)
SELECT
  sol.product_id,
  sol.placed::date AS sale_date,
  SUM(sol.quantity) AS units_sold
FROM sell_order_lines sol
WHERE sol.webshop_id = 1380
  AND sol.placed >= CURRENT_DATE - INTERVAL '365 days'
  AND sol.deleted_at IS NULL
GROUP BY sol.product_id, sol.placed::date
ORDER BY sol.product_id, sol.placed::date;

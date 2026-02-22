-- Block: fetch_stocks
-- Existing stock history from DB (already inserted). Use with product + sales data to simulate BOs only.
-- Same window as fetch_daily_sales (last 365 days), webshop 1380, whitelisted products.
SELECT
  s.product_id,
  s.date::date AS stock_date,
  s.on_hand
FROM stocks s
WHERE s.webshop_id = 1380
  AND s.deleted_at IS NULL
  AND s.date >= CURRENT_DATE - INTERVAL '365 days'
  AND s.product_id IN (
    28666283, 28666284, 28666285, 28666286, 28666287, 28666288, 28666289, 28666290,
    28666291, 28666292, 28666293, 28666294, 28666295, 28666296, 28666297, 28666298,
    28666299, 28666300, 28666301, 28666302, 28666303, 28666304, 28666305, 28666306,
    28666307, 28666308, 28666309, 28666310, 28666311, 28666312, 28666313, 28666314, 28666315, 28666316
  )
ORDER BY s.product_id, s.date;

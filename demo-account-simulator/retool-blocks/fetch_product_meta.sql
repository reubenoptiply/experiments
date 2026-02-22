-- Block A: fetch_product_meta
-- Joins webshop_products → supplier_products → suppliers → webshops
-- One row per product for webshop 1380, 32-ID whitelist (28666283–28666316)
SELECT
  wp.id AS product_id,
  wp.uuid AS product_uuid,
  wp.name AS product_name,
  wp.current_stock_on_hand AS starting_stock,
  wp.price AS sell_price,
  sp.price AS purchase_price,
  COALESCE(sp.delivery_time, s.delivery_time) AS lead_time,
  s.user_replenishment_period AS reorder_period,
  w.uuid AS webshop_uuid,
  s.id AS supplier_id,
  s.uuid AS supplier_uuid
FROM webshop_products wp
JOIN supplier_products sp ON wp.supplier_product_id = sp.id
JOIN suppliers s ON sp.supplier_id = s.id
JOIN webshops w ON wp.webshop_id = w.id
WHERE wp.webshop_id = 1380
  AND wp.deleted_at IS NULL
  AND wp.id IN (
    28666283, 28666284, 28666285, 28666286, 28666287, 28666288, 28666289, 28666290,
    28666291, 28666292, 28666293, 28666294, 28666295, 28666296, 28666297, 28666298,
    28666299, 28666300, 28666301, 28666302, 28666303, 28666304, 28666305, 28666306,
    28666307, 28666308, 28666309, 28666310, 28666311, 28666312, 28666313, 28666314, 28666315, 28666316
  );

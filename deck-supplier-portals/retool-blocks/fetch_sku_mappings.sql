-- Retool DB resource: fetch SKU mappings for the given supplier(s).
-- Bind :supplier_id to a single supplier ID, or :supplier_ids to an array for multiple.

SELECT supplier_id, optiply_sku, supplier_sku
FROM sku_mappings
WHERE supplier_id = CAST(:supplier_id AS TEXT);
-- For multiple suppliers: WHERE supplier_id = ANY(CAST(:supplier_ids AS TEXT[]))

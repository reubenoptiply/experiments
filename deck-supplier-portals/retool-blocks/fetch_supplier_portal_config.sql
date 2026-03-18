-- Retool DB resource: fetch Deck config for one or all suppliers.
-- For one supplier, bind :supplier_id. For all active, use: WHERE is_active = true AND (:supplier_id::text IS NULL OR supplier_id = :supplier_id)

SELECT id, supplier_id, supplier_name, source_guid, is_active
FROM supplier_portal_config
WHERE is_active = true
  AND (CAST(:supplier_id AS TEXT) IS NULL OR supplier_id = CAST(:supplier_id AS TEXT));

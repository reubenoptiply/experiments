-- Retool DB resource: fetch Deck config for one or all suppliers.
-- Bind :supplier_id from workflow run input, e.g. {{ startTrigger.supplier_id }}.

SELECT id, supplier_id, supplier_name, source_guid, is_active
FROM deck_supplier_portal_config
WHERE is_active = true
  AND (CAST(:supplier_id AS TEXT) IS NULL OR supplier_id = CAST(:supplier_id AS TEXT));

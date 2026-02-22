-- Soft-delete all existing stocks for webshop 1380 before insert_stocks runs.
UPDATE stocks
SET deleted_at = NOW()
WHERE webshop_id = 1380
  AND deleted_at IS NULL;

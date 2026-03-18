-- Retool DB resource: check if there is already an in-flight job for this supplier (connecting or adding_items).
-- Bind :supplier_id. If this returns any rows, do not start a new EnsureConnection for this supplier.

SELECT id, job_guid, supplier_id, status, updated_at
FROM deck_jobs
WHERE supplier_id = CAST(:supplier_id AS TEXT)
  AND status IN ('connecting', 'adding_items');

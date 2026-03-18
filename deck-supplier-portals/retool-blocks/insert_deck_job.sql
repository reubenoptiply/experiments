-- Retool DB resource: insert a new deck_job (status connecting). Bind :supplier_id, :customer_id, :bo_ids (JSON array), :items (JSON array).
-- Returns the inserted row including id and job_guid (job_guid set by workflow after Deck responds).

INSERT INTO deck_jobs (supplier_id, customer_id, bo_ids, items, status)
VALUES (
  CAST(:supplier_id AS TEXT),
  CAST(:customer_id AS TEXT),
  CAST(:bo_ids AS JSONB),
  CAST(:items AS JSONB),
  'connecting'
)
RETURNING id, job_guid, supplier_id, customer_id, bo_ids, items, status, created_at, updated_at;

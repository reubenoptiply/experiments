-- Retool DB resource: update deck_job by id or job_guid. Bind only the columns you want to update.
-- Examples:
--   Set job_guid after EnsureConnection submit: job_guid = :job_guid WHERE id = :id
--   Set access_token, status = adding_items: access_token = :access_token, status = 'adding_items', updated_at = now()
--   Set results, status completed/needs_review: results = :results, status = :status, updated_at = now()
--   Set failed: status = 'failed', error_message = :error_message, updated_at = now()

UPDATE deck_jobs
SET
  job_guid       = COALESCE(CAST(:job_guid AS TEXT), job_guid),
  access_token   = COALESCE(CAST(:access_token AS TEXT), access_token),
  status         = COALESCE(CAST(:status AS TEXT), status),
  results        = COALESCE(CAST(:results AS JSONB), results),
  error_message  = COALESCE(CAST(:error_message AS TEXT), error_message),
  updated_at     = now()
WHERE id = CAST(:id AS UUID);

-- Retool DB resource: find deck_jobs stuck in connecting or adding_items for more than 10 minutes.
-- Used by scheduled workflow deck-job-timeout-check (every 15 min). For each row, update status to failed and set error_message.

SELECT id, job_guid, supplier_id, status, updated_at
FROM deck_jobs
WHERE status IN ('connecting', 'adding_items')
  AND updated_at < now() - interval '10 minutes';

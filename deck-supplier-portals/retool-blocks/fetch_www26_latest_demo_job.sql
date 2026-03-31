-- Retool DB: latest WWW26 demo deck_job (for app polling after submit).
-- Expect customer_id = 'www26-demo' on jobs created by the demo submit workflow.

SELECT
  id,
  job_guid,
  supplier_id,
  customer_id,
  bo_id,
  items,
  status,
  results,
  error_message,
  created_at,
  updated_at
FROM deck_jobs
WHERE customer_id = 'www26-demo'
ORDER BY created_at DESC
LIMIT 1;

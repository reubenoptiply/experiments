-- Retool DB resource: fetch deck_job by job_guid (from webhook payload). Used in Workflow B to get access_token, items, id.

SELECT id, job_guid, supplier_id, customer_id, bo_id, items, access_token, status, results, error_message
FROM deck_jobs
WHERE job_guid = CAST(:job_guid AS TEXT)
LIMIT 1;

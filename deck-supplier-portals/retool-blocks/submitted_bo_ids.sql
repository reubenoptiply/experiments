-- Retool DB resource: list of BO IDs already in deck_jobs (not failed). Use to exclude from approved BO list.
-- Returns a single column 'bo_id' (text). In Retool, filter approved BOs in JS or exclude in query.

SELECT bo_id
FROM deck_jobs
WHERE status NOT IN ('failed');

-- Retool DB resource: mark a deck_job as failed (timeout). Bind :id (UUID), :error_message.

UPDATE deck_jobs
SET status = 'failed', error_message = CAST(:error_message AS TEXT), updated_at = now()
WHERE id = CAST(:id AS UUID)
RETURNING id, status, error_message;

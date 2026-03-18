-- Retool DB resource: list of BO IDs already in deck_jobs (not failed). Use to exclude from approved BO list.
-- Returns a single column 'bo_id' (text). In Retool, use this in fetch_approved_bos_optiply exclusion
-- or filter in JS: approvedBos.filter(b => !submittedBoIds.data.map(r => r.bo_id).includes(b.bo_id)).

SELECT DISTINCT jsonb_array_elements_text(dj.bo_ids) AS bo_id
FROM deck_jobs dj
WHERE dj.status NOT IN ('failed');

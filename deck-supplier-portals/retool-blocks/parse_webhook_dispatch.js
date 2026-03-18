/**
 * Parse Deck webhook payload and return dispatch info for Workflow B (webhook receiver).
 * Input: webhook payload (Retool: trigger block body or {{ startTrigger.body }}).
 * Output: { webhook_code, job_guid, action, access_token, output, error } so the workflow can branch.
 * action: 'EnsureConnection' | 'AddItemsToCart' | 'Error' | 'MfaRequired' | 'Unknown'
 */
function parseWebhookDispatch(payload) {
  const p = payload && typeof payload === 'object' ? payload : {};
  const webhookCode = p.webhook_code || p.webhook_type || '';
  const jobGuid = p.job_guid;
  const output = p.output;
  const error = p.error;

  let action = 'Unknown';
  if (webhookCode === 'EnsureConnection') action = 'EnsureConnection';
  else if (webhookCode === 'AddItemsToCart') action = 'AddItemsToCart';
  else if (webhookCode === 'Error') action = 'Error';
  else if (webhookCode === 'MfaRequired') action = 'MfaRequired';

  const access_token = output && output.access_token != null ? output.access_token : null;

  return {
    webhook_code: webhookCode,
    job_guid: jobGuid,
    action,
    access_token,
    output: output || null,
    error: error || null,
  };
}

// Retool: bind webhookPayload to the webhook trigger's body (e.g. startTrigger.body)
return parseWebhookDispatch(webhookPayload);

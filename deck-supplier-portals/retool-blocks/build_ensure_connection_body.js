/**
 * Build request body for Deck API: EnsureConnection.
 * Inputs (bind in Retool): source_guid, username, password (from deck_supplier_portal_config + env vars in pilot).
 * Output: { body } — JSON body for POST https://sandbox.deck.co/api/v1/jobs/submit (or live).
 */
function buildEnsureConnectionBody(sourceGuid, username, password) {
  const body = {
    job_code: 'EnsureConnection',
    input: {
      username: String(username ?? ''),
      password: String(password ?? ''),
      source_guid: String(sourceGuid ?? ''),
    },
  };
  return { body };
}

return buildEnsureConnectionBody(source_guid, username, password);

/**
 * Build request body for Deck API: CloseConnection.
 * Input: access_token (from EnsureConnection webhook, stored on deck_job).
 * Output: { body } — JSON body for POST .../jobs/submit. No webhook is returned.
 */
function buildCloseConnectionBody(accessToken) {
  const body = {
    job_code: 'CloseConnection',
    input: {
      access_token: String(accessToken ?? ''),
    },
  };
  return { body };
}

return buildCloseConnectionBody(access_token);

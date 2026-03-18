/**
 * Build request body for Deck API: AddItemsToCart.
 * Inputs (bind in Retool): access_token (from EnsureConnection webhook), items (from transform_bo_to_deck_items).
 * Output: { body } — JSON body for POST .../jobs/submit.
 */
function buildAddItemsToCartBody(accessToken, items) {
  const body = {
    job_code: 'AddItemsToCart',
    input: {
      access_token: String(accessToken ?? ''),
      items: Array.isArray(items) ? items : [],
    },
  };
  return { body };
}

return buildAddItemsToCartBody(access_token, items);

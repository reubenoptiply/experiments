/**
 * WWW26 demo — build lineItems[] for build_www26_email_html from deck_jobs.items JSON
 * (sku, quantity, expected_price only) plus a fixed SKU → product name map.
 *
 * Keep PRODUCT_NAMES in sync with sku list in www26_hardcoded_buy_order.js.
 *
 * Input: storedItems — JSON array from deck_jobs.items (same shape as itemsForDeck + optional fields)
 * Output: { lineItems } for build_www26_email_html
 */
const PRODUCT_NAMES = {
  'HA-2041': 'Schwarzkopf BC Color Freeze Shampoo 250ml',
  'HA-3087': 'Redken All Soft Conditioner 300ml',
  'HA-1556': 'Wella Professionals Oil Reflections Shampoo 1000ml',
  'HA-4210': "L'Oréal Serie Expert Vitamino Color Masque 250ml",
  'HA-0893': 'Moroccanoil Treatment Oil 100ml',
};

function mergeStoredItemsForEmail(storedItems) {
  const arr = Array.isArray(storedItems) ? storedItems : [];
  const lineItems = arr.map((row) => {
    const sku = String(row.sku ?? '');
    return {
      sku,
      productName: PRODUCT_NAMES[sku] || sku,
      qty: row.quantity != null ? row.quantity : row.qty,
      expectedPriceDisplay: row.expected_price != null ? String(row.expected_price) : '',
    };
  });
  return { lineItems };
}

return mergeStoredItemsForEmail(storedItems);

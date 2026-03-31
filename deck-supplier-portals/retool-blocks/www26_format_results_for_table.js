/**
 * WWW26 demo — merge AddItemsToCart webhook output with hardcoded line metadata for a Retool Table.
 *
 * Inputs:
 *   - lineItems — from www26_hardcoded_buy_order.lineItems (sku, productName, qty, expectedPriceDisplay)
 *   - resultsJson — deck_jobs.results (JSON) or output object; expects .items array from Deck
 *
 * Output: { rows } — each row: sku, productName, qty, expected, actual, stockLabel, priceLabel, cartLabel, rowClass
 */
function formatResultsForTable(lineItems, resultsJson) {
  const lines = Array.isArray(lineItems) ? lineItems : [];
  let items = [];
  if (resultsJson && typeof resultsJson === 'object') {
    if (Array.isArray(resultsJson.items)) items = resultsJson.items;
    else if (resultsJson.output && Array.isArray(resultsJson.output.items)) items = resultsJson.output.items;
  }
  const bySku = {};
  for (const it of items) {
    if (it && it.sku != null) bySku[String(it.sku)] = it;
  }

  const rows = lines.map((row) => {
    const d = bySku[row.sku];
    const added = d && d.added_to_cart === true;
    const status = (d && d.status) || '';

    let stockLabel = '—';
    if (!d) stockLabel = '…';
    else if (added) stockLabel = '✅ In stock';
    else stockLabel = status ? `❌ ${status}` : '❌ Not added';

    let priceLabel = '—';
    if (d && d.price_is) {
      if (d.price_is === 'As expected') priceLabel = 'As expected';
      else if (d.price_is === 'Higher than expected') priceLabel = '⚠️ Higher';
      else if (d.price_is === 'Lower than expected') priceLabel = '⚠️ Lower';
      else priceLabel = d.price_is;
    } else if (added) priceLabel = 'As expected';

    const actualPrice = d && d.price != null ? String(d.price) : '—';
    const cartLabel = !d ? '…' : added ? '✅ Added' : '❌ Not added';
    const rowClass = !d ? 'pending' : !added ? 'fail' : priceLabel.includes('⚠️') ? 'warn' : 'ok';

    return {
      sku: row.sku,
      productName: row.productName,
      qty: row.qty,
      expected: row.expectedPriceDisplay,
      actual: actualPrice,
      stockLabel,
      priceLabel,
      cartLabel,
      rowClass,
    };
  });

  return { rows };
}

return formatResultsForTable(lineItems, resultsJson);

/**
 * Transform Optiply BO line items into Deck AddItemsToCart format.
 * Inputs (bind in Retool):
 *   - lineItems: array from fetch_bo_line_items_optiply.data (rows with quantity, unit_price, optiply_sku, supplier_sku)
 *   - skuMappings: array from fetch_sku_mappings.data (optional; { optiply_sku, supplier_sku }) — used to override supplier_sku per product
 *   - currencySymbol: string, default "€"
 * Output: { items } — array of { sku, quantity, expected_price } for Deck API.
 */
function transformBoToDeckItems(lineItems, skuMappings, currencySymbol) {
  const symbol = currencySymbol == null ? '€' : currencySymbol;
  const mapByOptiplySku = (skuMappings || []).reduce((acc, row) => {
    acc[row.optiply_sku] = row.supplier_sku;
    return acc;
  }, {});

  const items = (lineItems || []).map((row) => {
    const sku = mapByOptiplySku[row.optiply_sku] != null
      ? mapByOptiplySku[row.optiply_sku]
      : (row.supplier_sku || row.optiply_sku);
    const price = row.unit_price != null ? Number(row.unit_price) : 0;
    const expected_price = `${symbol}${price.toFixed(2)}`;
    return { sku, quantity: Number(row.quantity) || 0, expected_price };
  });

  return { items };
}

// Retool: bind query inputs lineItems (fetch_bo_line_items_optiply.data), skuMappings (fetch_sku_mappings.data), currencySymbol (optional)
return transformBoToDeckItems(
  Array.isArray(lineItems) ? lineItems : [],
  Array.isArray(skuMappings) ? skuMappings : [],
  currencySymbol
);

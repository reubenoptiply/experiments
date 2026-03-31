/**
 * WWW26 demo — hardcoded Hairaction buy order (no Optiply fetch).
 * Use for Retool Workflow submit path and Retool App display.
 *
 * Output:
 *   - boRef, supplierName, portalHost, portalReviewUrl
 *   - lineItems[] — display fields (sku, productName, qty, expectedPriceDisplay, lineTotalDisplay)
 *   - itemsForDeck[] — { sku, quantity, expected_price } for Deck AddItemsToCart (currency in string)
 *   - itemCount, totalFormatted
 *
 * Bindings: none required.
 *
 * Important: Confirm SKUs against live hairaction.nl before recording; swap LINE_ITEMS if needed.
 */
const LINE_ITEMS = [
  {
    sku: 'HA-2041',
    productName: 'Schwarzkopf BC Color Freeze Shampoo 250ml',
    qty: 12,
    unitEur: 4.85,
  },
  {
    sku: 'HA-3087',
    productName: 'Redken All Soft Conditioner 300ml',
    qty: 8,
    unitEur: 11.2,
  },
  {
    sku: 'HA-1556',
    productName: 'Wella Professionals Oil Reflections Shampoo 1000ml',
    qty: 4,
    unitEur: 18.9,
  },
  {
    sku: 'HA-4210',
    productName: "L'Oréal Serie Expert Vitamino Color Masque 250ml",
    qty: 6,
    unitEur: 9.45,
  },
  {
    sku: 'HA-0893',
    productName: 'Moroccanoil Treatment Oil 100ml',
    qty: 5,
    unitEur: 41.44,
  },
];

function eurDisplay(n) {
  return `€${Number(n).toFixed(2)}`;
}

const lineItems = LINE_ITEMS.map((row) => {
  const lineTotal = row.qty * row.unitEur;
  return {
    sku: row.sku,
    productName: row.productName,
    qty: row.qty,
    expectedPriceDisplay: eurDisplay(row.unitEur),
    lineTotalDisplay: eurDisplay(lineTotal),
    unitEur: row.unitEur,
  };
});

const itemsForDeck = LINE_ITEMS.map((row) => ({
  sku: row.sku,
  quantity: row.qty,
  expected_price: eurDisplay(row.unitEur),
}));

const totalEur = LINE_ITEMS.reduce((s, row) => s + row.qty * row.unitEur, 0);

return {
  boRef: 'BO-2026-0412',
  supplierName: 'Hairaction',
  portalHost: 'hairaction.nl',
  portalReviewUrl: 'https://www.hairaction.nl',
  /** Use when inserting deck_jobs for the demo */
  demoCustomerId: 'www26-demo',
  /** Register this supplier_id in deck_supplier_portal_config with real Hairaction source_guid */
  demoSupplierId: 'hairaction-demo',
  lineItems,
  itemsForDeck,
  itemCount: LINE_ITEMS.length,
  totalFormatted: `€ ${totalEur.toFixed(2)}`,
};

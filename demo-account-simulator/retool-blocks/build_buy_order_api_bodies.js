// Retool JS block: build_buy_order_api_bodies
// Runs after simulate_stocks OR simulate_buy_orders_from_stocks. Reads buy_orders and builds JSON:API
// request bodies for POST https://api.optiply.com/v1/buyOrders?accountId=<accountId>
// BO-only path: use simulate_buy_orders_from_stocks (reads existing stocks from DB; no stock re-sim).

function toISOZ(dateStr) {
  if (!dateStr) return null;
  const s = String(dateStr).trim();
  if (s.includes("T")) return s.endsWith("Z") ? s : s + "Z";
  return s.replace(" ", "T") + "Z";
}

// Prefer BO-only source when stocks were not re-simulated; else full simulation output.
const boSource = simulate_buy_orders_from_stocks?.data ?? simulate_stocks?.data;
const buyOrders = boSource?.buy_orders;
const itemDeliveries = boSource?.item_deliveries ?? [];

if (!buyOrders || !Array.isArray(buyOrders)) {
  return {
    buy_order_bodies: [],
    item_deliveries_meta: [],
  };
}

const buy_order_bodies = buyOrders.map((bo) => {
  const quantity = Number(bo.quantity) || 0;
  const unitPrice = Number(bo.unit_price) || 0;
  const subtotalValue = Math.round(quantity * unitPrice * 100) / 100;
  const totalValue = subtotalValue;
  const placed = toISOZ(bo.placed);
  const expectedDeliveryDate = toISOZ(bo.expected_delivery_date);

  return {
    data: {
      type: "buyOrders",
      attributes: {
        orderLines: [
          {
            quantity,
            subtotalValue,
            productId: Number(bo.product_id),
            expectedDeliveryDate,
          },
        ],
        placed,
        expectedDeliveryDate,
        totalValue,
        supplierId: Number(bo.supplier_id),
        assembly: false,
      },
    },
  };
});

return {
  buy_order_bodies,
  item_deliveries_meta: Array.isArray(itemDeliveries) ? itemDeliveries : [],
};

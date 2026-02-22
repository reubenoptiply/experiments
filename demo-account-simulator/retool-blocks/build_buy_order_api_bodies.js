// Retool JS block: build_buy_order_api_bodies
// Runs after simulate_stocks. Reads buy_orders from simulation and builds JSON:API request bodies
// for POST https://api.optiply.com/v1/buyOrders?accountId=<accountId>
// In Retool: add a Loop block that POSTs each body; then use build_receipt_line_bodies after the loop.

function toISOZ(dateStr) {
  if (!dateStr) return null;
  const s = String(dateStr).trim();
  if (s.includes("T")) return s.endsWith("Z") ? s : s + "Z";
  return s.replace(" ", "T") + "Z";
}

const buyOrders = simulate_stocks?.data?.buy_orders;
const itemDeliveries = simulate_stocks?.data?.item_deliveries ?? [];

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

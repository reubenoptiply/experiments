// Retool JS block: build_assembly_order_api_bodies
// Builds JSON:API request bodies for assembly orders (assembly: true) from simulate_assembly_orders_from_stocks.data.

function toISOZ(dateStr) {
  if (!dateStr) return null;
  const s = String(dateStr).trim();
  if (s.includes("T")) return s.endsWith("Z") ? s : s + "Z";
  return s.replace(" ", "T") + "Z";
}

const boSource = simulate_assembly_orders_from_stocks?.data;
const buyOrders = boSource?.assembly_orders;
const itemDeliveries = boSource?.item_deliveries ?? [];

if (!buyOrders || !Array.isArray(buyOrders)) {
  return {
    assembly_order_bodies: [],
    item_deliveries_meta: [],
  };
}

const assembly_order_bodies = buyOrders.map((bo) => {
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
        assembly: true,
      },
    },
  };
});

return {
  assembly_order_bodies,
  item_deliveries_meta: Array.isArray(itemDeliveries) ? itemDeliveries : [],
};

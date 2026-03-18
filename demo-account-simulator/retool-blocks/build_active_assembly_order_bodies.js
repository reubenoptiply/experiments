// Retool JS block: build_active_assembly_order_bodies
// Builds a few assembly order POST bodies with expected_delivery_date in the future and no completed.
// These stay "active" (in transit). Input: fetch_product_meta.data (must include assembly product IDs
// 29177521, 29177522, 29177523 in the product list, or extend your fetch_product_meta query).
// Output: active_assembly_order_bodies — Loop POST to /v1/buyOrders?accountId=...

const ASSEMBLY_PRODUCT_IDS = [29177521, 29177522, 29177523];

function toISOZ(dateStr) {
  if (!dateStr) return null;
  const s = String(dateStr).trim();
  if (s.includes("T")) return s.endsWith("Z") ? s : s + "Z";
  return s.replace(" ", "T") + "Z";
}

function addDaysFromNow(days) {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() + days);
  d.setUTCHours(12, 0, 0, 0);
  return d.toISOString();
}

const products = fetch_product_meta?.data ?? [];
const assemblyProducts = (Array.isArray(products) ? products : []).filter((p) =>
  ASSEMBLY_PRODUCT_IDS.includes(Number(p.product_id))
);

if (assemblyProducts.length === 0) {
  return { active_assembly_order_bodies: [] };
}

// Build one order per assembly product, up to 3. Future expected_delivery_date (e.g. +14 days).
const now = toISOZ(new Date().toISOString());
const futureDate = addDaysFromNow(14);
const howMany = Math.min(3, assemblyProducts.length);

const active_assembly_order_bodies = assemblyProducts.slice(0, howMany).map((p) => {
  const quantity = 10;
  const unitPrice = Number(p.purchase_price) || 0;
  const subtotalValue = Math.round(quantity * unitPrice * 100) / 100;
  return {
    data: {
      type: "buyOrders",
      attributes: {
        orderLines: [
          {
            quantity,
            subtotalValue,
            productId: Number(p.product_id),
            expectedDeliveryDate: futureDate,
          },
        ],
        placed: now,
        expectedDeliveryDate: futureDate,
        totalValue: subtotalValue,
        supplierId: Number(p.supplier_id),
        assembly: true,
      },
    },
  };
});

return { active_assembly_order_bodies };

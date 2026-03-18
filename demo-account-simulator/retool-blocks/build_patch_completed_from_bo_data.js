// Retool JS block: build_patch_completed_from_bo_data
// Uses the same SQL as receipt lines: fetch_bo_data_assembly.data or fetch_bo_data.data.
// Dedupes by bo_id and builds PATCH bodies so buy_order.completed = buy_order.expected_delivery_date
// for every BO (no skip, no random late). Use with Loop: PATCH /v1/buyOrders/{{ item.id }}?accountId=...

function toISOZ(dateStr) {
  if (!dateStr) return null;
  const s = String(dateStr).trim();
  if (s.includes("T")) return s.endsWith("Z") ? s : s + "Z";
  return s.replace(" ", "T") + "Z";
}

const rows = fetch_bo_data_assembly?.data ?? fetch_bo_data?.data ?? [];

if (!Array.isArray(rows) || rows.length === 0) {
  return { patch_items: [], count: 0 };
}

const seen = new Set();
const patch_items = [];

for (const r of rows) {
  const bo_id = r.bo_id;
  if (bo_id == null || seen.has(bo_id)) continue;
  seen.add(bo_id);
  const expectedStr = r.bo_expected_delivery_date ?? r.expected_delivery_date;
  patch_items.push({
    id: bo_id,
    body: {
      data: {
        type: "buyOrders",
        attributes: {
          completed: toISOZ(expectedStr),
        },
      },
    },
  });
}

return {
  patch_items,
  count: patch_items.length,
};

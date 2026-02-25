// Retool JS block: build_receipt_line_bodies_from_bo_data
// Builds receipt line (item delivery) API bodies from fetch_bo_data.data (SQL output).
// Use this when BOs already exist in DB: run fetch_bo_data SQL, then this block, then Loop POST receiptLines.
// No need for create responses — each row has bol_id, quantity, and expected_delivery_date for "occurred".

function toISOZ(dateStr) {
  if (!dateStr) return null;
  const s = String(dateStr).trim();
  if (s.includes("T")) return s.endsWith("Z") ? s : s + "Z";
  return s.replace(" ", "T") + "Z";
}

const rows = fetch_bo_data?.data ?? [];

if (!Array.isArray(rows) || rows.length === 0) {
  return [];
}

const receipt_line_bodies = rows.map((r) => {
  const buyOrderLineId = r.bol_id;
  const occurred = r.bol_expected_delivery_date ?? r.bo_expected_delivery_date ?? r.expected_delivery_date;
  const quantity = Number(r.quantity) || 0;
  if (buyOrderLineId == null) return null;
  return {
    data: {
      type: "receiptLines",
      attributes: {
        occurred: toISOZ(occurred),
        quantity,
        buyOrderLineId,
      },
    },
  };
}).filter(Boolean);

return receipt_line_bodies;

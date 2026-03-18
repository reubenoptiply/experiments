// Retool JS block: build_assembly_receipt_line_bodies
// Builds receipt line API bodies from the SQL block that returns BO/BOL data (fetch_bo_data_assembly
// or fetch_bo_data). Use when assembly orders already exist in DB: run fetch_bo_data_assembly (or
// fetch_bo_data), then this block, then Loop POST receiptLines.
// POST https://api.optiply.com/v1/receiptLines?accountId=<accountId>

function toISOZ(dateStr) {
  if (!dateStr) return null;
  const s = String(dateStr).trim();
  if (s.includes("T")) return s.endsWith("Z") ? s : s + "Z";
  return s.replace(" ", "T") + "Z";
}

const rows = fetch_bo_data_assembly?.data ?? fetch_bo_data?.data ?? [];

if (!Array.isArray(rows) || rows.length === 0) {
  return { receipt_line_bodies: [] };
}

const receipt_line_bodies = rows
  .map((r) => {
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
  })
  .filter(Boolean);

return { receipt_line_bodies };

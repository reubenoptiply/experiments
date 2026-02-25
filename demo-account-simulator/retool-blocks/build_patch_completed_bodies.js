// Retool JS block: build_patch_completed_bodies
// Builds PATCH bodies to set "completed" on buy orders that are already delivered (expected date in the past).
// Use the array of CREATE responses from your "POST buy orders" Loop (each response must include id + expectedDeliveryDate).
// ~80% get completed = expectedDeliveryDate; ~20% get completed = expectedDeliveryDate + 1–5 days (late).
// Future-dated BOs (expectedDeliveryDate > today) are skipped and not patched.

function parseDate(str) {
  if (!str) return null;
  const s = String(str).trim();
  const d = new Date(s);
  return isNaN(d.getTime()) ? null : d;
}

function toISOZ(date) {
  if (!date) return null;
  const d = date instanceof Date ? date : new Date(date);
  return d.toISOString ? d.toISOString() : null;
}

function addDays(isoStr, days) {
  const d = parseDate(isoStr);
  if (!d) return isoStr;
  d.setUTCDate(d.getUTCDate() + days);
  return toISOZ(d);
}

// Input: either (1) fetch_bo_data.data — rows with bo_id, bo_expected_delivery_date (deduped by bo_id), or
// (2) array of BOs: Create response { data: { id, attributes: { expectedDeliveryDate } } } / flat { id, expectedDeliveryDate }, or
// (3) request bodies + bo_ids_in_order (array of ids in same order).
const rawInput = fetch_bo_data?.data ?? patch_source_bo_list?.data ?? patch_source_bo_list ?? post_buy_orders_loop?.data ?? post_buy_orders_loop ?? [];
const boIdsInOrder = typeof bo_ids_in_order !== "undefined" ? (bo_ids_in_order?.data ?? bo_ids_in_order) : null;

// If input is from fetch_bo_data: rows have bo_id, bo_expected_delivery_date (or expected_delivery_date). Dedupe by bo_id.
let boList = rawInput;
const isBoDataRows = Array.isArray(rawInput) && rawInput.length > 0 && (rawInput[0].bo_id != null || rawInput[0].bo_expected_delivery_date != null);
if (isBoDataRows) {
  const seen = new Set();
  boList = rawInput.filter((r) => {
    const bid = r.bo_id;
    if (seen.has(bid)) return false;
    seen.add(bid);
    return true;
  });
}

const today = new Date();
today.setUTCHours(23, 59, 59, 999);

const patch_items = [];

for (let i = 0; i < boList.length; i++) {
  const raw = boList[i];
  const data = raw?.data ?? raw;
  let id = data?.id ?? raw?.id ?? raw?.bo_id;
  if (id == null && Array.isArray(boIdsInOrder) && boIdsInOrder[i] != null) {
    id = boIdsInOrder[i];
  }
  const attrs = data?.attributes ?? data;
  const expectedStr =
    attrs?.expectedDeliveryDate ?? raw?.expectedDeliveryDate ?? raw?.bo_expected_delivery_date ?? raw?.expected_delivery_date;
  const expectedDate = parseDate(expectedStr);
  if (expectedDate == null || id == null) continue;
  // Skip future-dated BOs — do not set completed
  if (expectedDate > today) continue;

  const isLate = Math.random() < 0.2; // ~20% late
  const completedStr = isLate
    ? addDays(expectedStr, 1 + Math.floor(Math.random() * 5)) // 1–5 days late
    : expectedStr;

  // id is for the URL (PATCH /v1/buyOrders/{{ item.id }}), not sent in the body
  patch_items.push({
    id,
    body: {
      data: {
        type: "buyOrders",
        attributes: {
          completed: completedStr,
        },
      },
    },
  });
}

return {
  patch_items,
  count: patch_items.length,
};

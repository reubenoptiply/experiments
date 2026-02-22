// Retool JS block: build_receipt_line_bodies
// Runs after the Retool Loop that POSTs buy orders (e.g. post_buy_orders_loop).
// In Retool: bind the Loop block's output so we have an array of responses (one per buy order).
// Extracts buyOrderLineId from each response and builds JSON:API bodies for
// POST https://api.optiply.com/v1/receiptLines?accountId=<accountId>

// Path to the line id in each create-buy-order response. Adjust if your API returns a different shape.
// Common: response.data.attributes.orderLines[0].id or response.data.included[0].id
function getBuyOrderLineIdFromResponse(response) {
  if (!response) return null;
  const d = response.data ?? response;
  const attrs = d?.attributes ?? d?.data?.attributes;
  const lines = attrs?.orderLines;
  if (Array.isArray(lines) && lines.length > 0 && lines[0].id != null) return lines[0].id;
  if (typeof lines?.[0]?.id === "number") return lines[0].id;
  const inc = d?.included ?? d?.data?.included;
  if (Array.isArray(inc)) {
    const line = inc.find((x) => x.type === "buyOrderLines" || x.type === "buy-order-lines");
    if (line?.id != null) return line.id;
  }
  return null;
}

function toISOZ(dateStr) {
  if (!dateStr) return null;
  const s = String(dateStr).trim();
  if (s.includes("T")) return s.endsWith("Z") ? s : s + "Z";
  return s.replace(" ", "T") + "Z";
}

const itemDeliveriesMeta = build_buy_order_api_bodies?.data?.item_deliveries_meta ?? simulate_stocks?.data?.item_deliveries ?? [];
// In Retool: replace post_buy_orders_loop with the name of your Loop block that POSTs buy orders.
// It should expose an array of responses (one per iteration). Retool often puts this in .data or .result.
const raw = typeof post_buy_orders_loop !== "undefined" ? (post_buy_orders_loop?.data ?? post_buy_orders_loop?.result ?? post_buy_orders_loop) : [];
const boResponses = Array.isArray(raw) ? raw : (raw?.data && Array.isArray(raw.data) ? raw.data : []);

if (!Array.isArray(itemDeliveriesMeta) || itemDeliveriesMeta.length === 0) {
  return { receipt_line_bodies: [] };
}

const lineIds = [];
for (let i = 0; i < boResponses.length; i++) {
  const resp = Array.isArray(boResponses) ? boResponses[i] : boResponses;
  lineIds.push(getBuyOrderLineIdFromResponse(resp));
}

const receipt_line_bodies = itemDeliveriesMeta
  .map((d) => {
    const orderIndex = d.order_index;
    const buyOrderLineId = lineIds[orderIndex];
    if (buyOrderLineId == null) return null;
    return {
      data: {
        type: "receiptLines",
        attributes: {
          occurred: toISOZ(d.delivered_at),
          quantity: Number(d.quantity) || 0,
          buyOrderLineId,
        },
      },
    };
  })
  .filter(Boolean);

return { receipt_line_bodies };

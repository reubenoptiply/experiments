/**
 * WWW26 demo — transactional HTML email body after AddItemsToCart.
 * Use in Workflow B (Send Email block, HTML body) and optionally in the App for preview.
 *
 * Inputs (bind in Retool):
 *   - boRef (string)
 *   - portalName (string) e.g. "hairaction.nl" (used in body copy)
 *   - portalReviewUrl (string) e.g. "https://www.hairaction.nl"
 *   - supplierBrand (string, optional) e.g. "Hairaction" — used in subject; defaults to "Hairaction"
 *   - lineItems — array of { sku, productName, qty, expectedPriceDisplay } (from www26_hardcoded_buy_order or merged)
 *   - deckItems — output.items from AddItemsToCart webhook: { sku, status, price, price_is, added_to_cart }
 *
 * Output: { subject, html } — subject matches spec; html is a single string for Send Email.
 */
function escapeHtml(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function buildWww26EmailHtml(boRef, portalName, portalReviewUrl, lineItems, deckItems, supplierBrand) {
  const lines = Array.isArray(lineItems) ? lineItems : [];
  const deckBySku = {};
  for (const it of Array.isArray(deckItems) ? deckItems : []) {
    if (it && it.sku != null) deckBySku[String(it.sku)] = it;
  }

  let added = 0;
  const summaryRows = [];

  for (const row of lines) {
    const d = deckBySku[row.sku] || {};
    const inCart = d.added_to_cart === true;
    if (inCart) added++;

    let icon = '❌';
    let detail = `${escapeHtml(row.productName)} × ${row.qty} — not added`;
    if (inCart) {
      const priceIs = d.price_is || '';
      const hasPriceWarn = priceIs && priceIs !== 'As expected';
      icon = hasPriceWarn ? '⚠️' : '✅';
      const actual = d.price != null ? String(d.price) : row.expectedPriceDisplay;
      if (hasPriceWarn) {
        detail = `${escapeHtml(row.productName)} × ${row.qty} — ${escapeHtml(actual)} (expected ${escapeHtml(row.expectedPriceDisplay)})`;
      } else {
        detail = `${escapeHtml(row.productName)} × ${row.qty} — ${escapeHtml(actual)}`;
      }
    } else if (d.status) {
      detail = `${escapeHtml(row.productName)} × ${row.qty} — ${escapeHtml(d.status)}`;
    }

    summaryRows.push(`<tr><td style="padding:8px 0;font-size:14px;color:#374151;">${icon} ${detail}</td></tr>`);
  }

  const total = lines.length;
  const brand = supplierBrand && String(supplierBrand).trim() ? String(supplierBrand).trim() : 'Hairaction';
  const subject = `Your order has been added to the cart — ${brand}`;

  const html = `<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f4f5f7;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f4f5f7;padding:24px 16px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" style="max-width:560px;background:#ffffff;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,0.08);" cellspacing="0" cellpadding="0">
          <tr>
            <td style="padding:28px 28px 8px;">
              <p style="margin:0 0 16px;font-size:15px;line-height:1.6;color:#374151;">Hi there,</p>
              <p style="margin:0 0 16px;font-size:15px;line-height:1.6;color:#374151;">
                Great news! Your Buy Order <strong>${escapeHtml(boRef)}</strong> has been processed.
                <strong>${added} of ${total} items</strong> have been added to your cart on <strong>${escapeHtml(portalName)}</strong>.
              </p>
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin:16px 0;">
                ${summaryRows.join('\n')}
              </table>
              <p style="margin:20px 0 16px;font-size:15px;line-height:1.6;color:#374151;">
                Please review your cart and complete the order.
              </p>
              <a href="${escapeHtml(portalReviewUrl)}" style="display:inline-block;background:#7c3aed;color:#ffffff;text-decoration:none;padding:12px 24px;border-radius:6px;font-size:14px;font-weight:600;">
                Review &amp; Finalize Order →
              </a>
              <p style="margin:28px 0 0;font-size:12px;line-height:1.5;color:#9ca3af;">
                This order was placed automatically by Optiply.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>`;

  return { subject, html };
}

return buildWww26EmailHtml(boRef, portalName, portalReviewUrl, lineItems, deckItems, supplierBrand);

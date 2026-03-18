/**
 * Compute deck_job status from AddItemsToCart webhook output: 'completed' or 'needs_review'.
 * needs_review if any item has added_to_cart === false or price_is !== 'As expected'.
 * Input: output from AddItemsToCart webhook (output.items array).
 * Output: { status, failedCount, priceMismatchCount }.
 */
function computeAddItemsStatus(output) {
  const items = (output && output.items) ? output.items : [];
  let failedCount = 0;
  let priceMismatchCount = 0;
  for (const it of items) {
    if (it.added_to_cart === false) failedCount++;
    if (it.price_is && it.price_is !== 'As expected') priceMismatchCount++;
  }
  const status = (failedCount > 0 || priceMismatchCount > 0) ? 'needs_review' : 'completed';
  return { status, failedCount, priceMismatchCount };
}

return computeAddItemsStatus(addItemsOutput);

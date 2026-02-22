# Retool Python block: simulate_buy_orders_from_stocks
# Uses EXISTING stock data from DB (no stock re-simulation). Reads product + sales + stocks,
# infers delivery events (stock increases after sales) and back-calculates buy orders.
# Output: { buy_orders, item_deliveries } — same shape as simulate_stocks for build_buy_order_api_bodies.
# Inputs: fetch_product_meta.data, fetch_daily_sales.data, fetch_stocks.data

from datetime import datetime, timedelta


def build_sales_map(daily_sales):
    """sales_map[product_id][date_str] = units_sold."""
    sales_map = {}
    for row in daily_sales:
        p_id = int(row["product_id"])
        sale_date = row["sale_date"]
        date_str = sale_date.strftime("%Y-%m-%d") if hasattr(sale_date, "strftime") else str(sale_date)[:10]
        units_sold = int(row["units_sold"])
        if p_id not in sales_map:
            sales_map[p_id] = {}
        sales_map[p_id][date_str] = sales_map[p_id].get(date_str, 0) + units_sold
    return sales_map


def build_stock_series(stocks_rows):
    """Per product: list of (date_str, on_hand) sorted by date."""
    by_product = {}
    for row in stocks_rows:
        p_id = int(row["product_id"])
        d = row["stock_date"]
        date_str = d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)[:10]
        on_hand = int(row["on_hand"])
        if p_id not in by_product:
            by_product[p_id] = []
        by_product[p_id].append((date_str, on_hand))
    for p_id in by_product:
        by_product[p_id].sort(key=lambda x: x[0])
    return by_product


def infer_buy_orders_one_product(product_row, product_sales_map, product_stock_series):
    """From existing stock series + sales, infer deliveries and buy orders. Returns (buy_orders, item_deliveries)."""
    p_id = int(product_row["product_id"])
    product_uuid = str(product_row["product_uuid"])
    webshop_uuid = str(product_row["webshop_uuid"])
    lead_time = int(product_row.get("lead_time") or 14)
    unit_price = round(float(product_row.get("purchase_price") or 0), 2)
    supplier_id = product_row.get("supplier_id")
    supplier_uuid = product_row.get("supplier_uuid")
    if supplier_id is None or not supplier_uuid:
        return [], []

    buy_orders = []
    item_deliveries = []
    series = product_stock_series or []
    if len(series) < 2:
        return [], []

    for i in range(1, len(series)):
        prev_date_str, prev_on_hand = series[i - 1]
        curr_date_str, curr_on_hand = series[i]
        sales_today = product_sales_map.get(curr_date_str, 0)
        # delivery = curr_on_hand - (prev_on_hand - sales_today) = curr_on_hand - prev_on_hand + sales_today
        delivery_qty = curr_on_hand - prev_on_hand + sales_today
        if delivery_qty <= 0:
            continue

        delivered_at = curr_date_str + " 00:00:02"
        try:
            curr_dt = datetime.strptime(curr_date_str, "%Y-%m-%d")
            placed_dt = curr_dt - timedelta(days=lead_time)
            placed_ts = placed_dt.strftime("%Y-%m-%d") + " 00:00:02"
            expected_date = curr_date_str + " 00:00:02"
        except Exception:
            placed_ts = curr_date_str + " 00:00:02"
            expected_date = curr_date_str + " 00:00:02"

        order_index = len(buy_orders)
        buy_orders.append({
            "webshop_id": 1380,
            "webshop_uuid": webshop_uuid,
            "supplier_id": int(supplier_id),
            "supplier_uuid": str(supplier_uuid),
            "placed": placed_ts,
            "expected_delivery_date": expected_date,
            "product_id": p_id,
            "product_uuid": product_uuid,
            "quantity": int(delivery_qty),
            "unit_price": unit_price,
        })
        item_deliveries.append({
            "order_index": order_index,
            "product_id": p_id,
            "product_uuid": product_uuid,
            "quantity": int(delivery_qty),
            "delivered_at": delivered_at,
        })

    return buy_orders, item_deliveries


# --- Retool entry point (bindings: fetch_product_meta.data, fetch_daily_sales.data, fetch_stocks.data) ---
products = fetch_product_meta.data
daily_sales = fetch_daily_sales.data
stocks_rows = fetch_stocks.data

if not isinstance(products, list):
    products = []
if not isinstance(daily_sales, list):
    daily_sales = []
if not isinstance(stocks_rows, list):
    stocks_rows = []

sales_map = build_sales_map(daily_sales)
stock_series = build_stock_series(stocks_rows)

all_buy_orders = []
all_item_deliveries = []

for product_row in products:
    p_id = int(product_row["product_id"])
    product_sales_map = sales_map.get(p_id, {})
    product_stock_series = stock_series.get(p_id, [])
    bos, deliveries = infer_buy_orders_one_product(product_row, product_sales_map, product_stock_series)
    base_index = len(all_buy_orders)
    all_buy_orders.extend(bos)
    for d in deliveries:
        d = dict(d)
        d["order_index"] = base_index + d["order_index"]
        all_item_deliveries.append(d)

return {
    "buy_orders": all_buy_orders,
    "item_deliveries": all_item_deliveries,
}

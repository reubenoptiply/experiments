# Retool Python block: simulate_stocks
# Demand from real fetch_daily_sales data; archetype governs ROP and stockout policy only.
# All products from fetch_product_meta are simulated (including composed products / kits).
# Stock is driven by real sales so the stock graph matches the sales graph; Stockout Prone gets one forced stockout in the last 3 months.

import math
import random
from datetime import datetime, timedelta, date


def build_sales_map(daily_sales):
    """Build nested dict sales_map[product_id][date_str] = units_sold.
    date_str format YYYY-MM-DD to match (today - 365 + day).strftime("%Y-%m-%d").
    """
    sales_map = {}
    for row in daily_sales:
        p_id = int(row["product_id"])
        sale_date = row["sale_date"]
        if hasattr(sale_date, "strftime"):
            date_str = sale_date.strftime("%Y-%m-%d")
        else:
            date_str = str(sale_date)[:10]
        units_sold = int(row["units_sold"])
        if p_id not in sales_map:
            sales_map[p_id] = {}
        sales_map[p_id][date_str] = sales_map[p_id].get(date_str, 0) + units_sold
    return sales_map


def parse_archetype(name):
    """Extract text inside (...) and map to canonical archetype string.
    Handles nested parens e.g. 'Product (Stockout Prone (Demand))' -> 'Stockout Prone (Demand)'.
    """
    if not name or "(" not in name or ")" not in name:
        return "stable"
    start = name.index("(") + 1
    end = name.rindex(")")  # last closing paren so nested archetypes work
    if start >= end:
        return "stable"
    extracted = name[start:end].strip()
    if "Stockout Prone" in extracted:
        return "stockout_prone"
    if "Seasonal" in extracted and "Summer" in extracted:
        return "seasonal_summer"
    if "Seasonal" in extracted and ("Winter" in extracted or "Holiday" in extracted):
        return "seasonal_winter"
    if "Negative Trend" in extracted:
        return "trend_down"
    if "Positive Trend" in extracted or ("Trend" in extracted and "Negative" not in extracted):
        return "trend"
    if "Step Change" in extracted and "Up" in extracted:
        return "step_up"
    if "Step Change" in extracted and "Down" in extracted:
        return "step_down"
    if "New Launch" in extracted:
        return "new_launch"
    if "Obsolete" in extracted or "Dead" in extracted:
        return "obsolete"
    if "Lumpy" in extracted or "Sporadic" in extracted:
        return "lumpy"
    if "Outlier" in extracted or "Influencer" in extracted:
        return "outlier"
    if "Container Filler" in extracted:
        return "container_filler"
    if "Micro-Seasonality" in extracted:
        return "micro_seasonal"
    return "stable"


def is_good_product(archetype):
    """Returns True if archetype is not stockout_prone, obsolete, or lumpy."""
    return archetype not in ("stockout_prone", "obsolete", "lumpy")


def seasonal_rop_active(curr_date, archetype):
    """Returns True if curr_date falls within 60 days before the archetype's peak.
    seasonal_summer: peak July 15, window May 16 – July 15.
    seasonal_winter: peak December 15, window October 16 – December 15.
    """
    if archetype == "seasonal_summer":
        # May 16 – July 15
        if curr_date.month < 5:
            return False
        if curr_date.month > 7:
            return False
        if curr_date.month == 5 and curr_date.day < 16:
            return False
        if curr_date.month == 7 and curr_date.day > 15:
            return False
        return True
    if archetype == "seasonal_winter":
        # October 16 – December 15
        if curr_date.month < 10:
            return False
        if curr_date.month > 12:
            return False
        if curr_date.month == 10 and curr_date.day < 16:
            return False
        if curr_date.month == 12 and curr_date.day > 15:
            return False
        return True
    return False


def simulate_one_product(product_row, product_sales_map, today):
    """Simulate 366 days of stock for one product. Returns (stock_rows, buy_orders, item_deliveries)."""
    p_id = int(product_row["product_id"])
    product_uuid = str(product_row["product_uuid"])
    webshop_uuid = str(product_row["webshop_uuid"])
    lead_time = int(product_row["lead_time"] or 14)
    reorder_period = int(product_row["reorder_period"] or 30)
    starting_stock = int(product_row["starting_stock"] or 0)
    unit_price = float(product_row.get("purchase_price") or 0)
    supplier_id = int(product_row["supplier_id"]) if product_row.get("supplier_id") is not None else None
    supplier_uuid = str(product_row["supplier_uuid"]) if product_row.get("supplier_uuid") else None
    archetype = parse_archetype(product_row.get("product_name") or product_row.get("name") or "")

    total_sold = sum(product_sales_map.values())
    avg_daily = max(1, total_sold // 366)

    if archetype == "stockout_prone":
        reorder_point = lead_time * avg_daily * 0.6
    else:
        reorder_point = lead_time * avg_daily * 1.5
    reorder_point = max(0, int(reorder_point))

    reorder_qty = max(1, int(avg_daily * reorder_period))

    if archetype == "new_launch":
        sim_stock = 0
    elif archetype == "obsolete":
        sim_stock = starting_stock + 600
    elif archetype == "lumpy":
        sim_stock = 60
    elif archetype == "container_filler":
        sim_stock = starting_stock + int(avg_daily * lead_time * 4)
    else:
        sim_stock = starting_stock + int(avg_daily * lead_time * 2)

    # (delivery_day_index, qty, order_index) so we can emit item_deliveries when received
    pending_deliveries = []
    stock_rows = []
    buy_orders = []
    item_deliveries = []
    stockout_count = 0
    in_stockout = False
    rop_boost_applied = False
    # Stockout Prone: force one day in the last 3 months to 0 so the stock graph shows a clear stockout
    LAST_3M_START = 276
    force_stockout_day = 300 if archetype == "stockout_prone" else -1

    start_date = today - timedelta(days=365)
    for day in range(366):
        curr_date = start_date + timedelta(days=day)
        date_str = curr_date.strftime("%Y-%m-%d")
        placed_ts = date_str + " 00:00:02"

        # (a) Active ROP
        active_rop = reorder_point
        if seasonal_rop_active(curr_date, archetype):
            active_rop = int(lead_time * avg_daily * 2.5)
        if archetype == "stockout_prone":
            active_rop = int(lead_time * avg_daily * 0.6)
        if archetype == "container_filler":
            active_rop = int(lead_time * avg_daily * 3.0)
        if archetype == "micro_seasonal" and curr_date.month in (2, 3, 8, 9):
            active_rop = int(lead_time * avg_daily * 2.0)
        if archetype in ("step_up", "trend") and day >= 180:
            active_rop = int(lead_time * avg_daily * 2.5)
        if archetype in ("step_down", "trend_down") and day >= 180:
            active_rop = int(lead_time * avg_daily * 0.8)
        if archetype == "obsolete" and day > 305:
            active_rop = -9999
        if rop_boost_applied:
            active_rop = active_rop + int(7 * avg_daily)

        # (b) Process inbound deliveries and emit item_deliveries
        still_pending = []
        for entry in pending_deliveries:
            delivery_day_index, qty, order_index = entry
            if delivery_day_index <= day:
                sim_stock += qty
                delivery_date = start_date + timedelta(days=delivery_day_index)
                item_deliveries.append({
                    "order_index": order_index,
                    "product_id": p_id,
                    "product_uuid": product_uuid,
                    "quantity": qty,
                    "delivered_at": delivery_date.strftime("%Y-%m-%d") + " 00:00:02",
                })
            else:
                still_pending.append(entry)
        pending_deliveries = still_pending

        # (c) Subtract sales
        units_sold = product_sales_map.get(date_str, 0)
        sold = min(units_sold, sim_stock)
        sim_stock = max(0, sim_stock - sold)

        # (d) Track stockouts
        if sim_stock == 0 and sold < units_sold:
            if not in_stockout:
                stockout_count += 1
                in_stockout = True
            if is_good_product(archetype) and stockout_count >= 2 and not rop_boost_applied:
                rop_boost_applied = True
        else:
            in_stockout = False

        # (e) ROP check and reorder — emit buy_order and track for delivery (include composed products if they have supplier)
        incoming = sum(qty for (_, qty, _) in pending_deliveries)
        if (sim_stock + incoming) < active_rop and supplier_id is not None and supplier_uuid:
            variance = random.randint(-2, 3)
            actual_lead = max(1, lead_time + variance)
            delivery_day = day + actual_lead
            expected_date = (start_date + timedelta(days=delivery_day)).strftime("%Y-%m-%d") + " 00:00:02"
            order_index = len(buy_orders)
            buy_orders.append({
                "webshop_id": 1380,
                "webshop_uuid": webshop_uuid,
                "supplier_id": supplier_id,
                "supplier_uuid": supplier_uuid,
                "placed": placed_ts,
                "expected_delivery_date": expected_date,
                "product_id": p_id,
                "product_uuid": product_uuid,
                "quantity": reorder_qty,
                "unit_price": round(unit_price, 2),
            })
            pending_deliveries.append((delivery_day, reorder_qty, order_index))

        # Stockout Prone: force one day in the last 3 months to 0 so the stock graph clearly shows a stockout
        if force_stockout_day >= 0 and day == force_stockout_day:
            sim_stock = 0

        # (f) Stock row
        stock_rows.append({
            "product_id": p_id,
            "product_uuid": product_uuid,
            "webshop_id": 1380,
            "webshop_uuid": webshop_uuid,
            "on_hand": int(sim_stock),
            "date": curr_date.strftime("%Y-%m-%d") + " 00:00:02",
        })

    return (stock_rows, buy_orders, item_deliveries)


# --- Retool entry point (input bindings) ---
products = fetch_product_meta.data
daily_sales = fetch_daily_sales.data

if not isinstance(products, list):
    products = []
if not isinstance(daily_sales, list):
    daily_sales = []

sales_map = build_sales_map(daily_sales)
today = datetime.utcnow().date()
all_stocks = []
all_buy_orders = []
all_item_deliveries = []

for product_row in products:
    p_id = int(product_row["product_id"])
    product_sales_map = sales_map.get(p_id, {})
    stock_rows, buy_orders, item_deliveries = simulate_one_product(product_row, product_sales_map, today)
    all_stocks.extend(stock_rows)
    base_index = len(all_buy_orders)
    all_buy_orders.extend(buy_orders)
    for d in item_deliveries:
        d = dict(d)
        d["order_index"] = base_index + d["order_index"]
        all_item_deliveries.append(d)

return {
    "stocks": all_stocks,
    "buy_orders": all_buy_orders,
    "item_deliveries": all_item_deliveries,
}

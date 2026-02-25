# Retool Python block: simulate stock histories from real sales + delivery data.
# Uses fetch_product_meta, fetch_daily_sales, fetch_bo_data, fetch_deliveries.
# Returns { stocks, product_count, stock_rows }.

import random
from datetime import datetime, timedelta

random.seed(42)

ASSEMBLED_SUPPLIER_ID = 785255


def build_sales_map(daily_sales):
    sales_map = {}
    for row in daily_sales:
        p_id = int(row["product_id"])
        d = row["sale_date"]
        date_str = d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)[:10]
        p_sales = sales_map.setdefault(p_id, {})
        p_sales[date_str] = p_sales.get(date_str, 0) + int(row["units_sold"])
    return sales_map


def build_delivery_map(bo_data, delivery_data):
    bol_to_product = {}
    for row in (bo_data or []):
        bol_to_product[int(row["bol_id"])] = int(row["webshop_product_id"])

    delivery_map = {}
    for row in (delivery_data or []):
        p_id = bol_to_product.get(int(row["buy_order_line_id"]))
        if p_id is None:
            continue
        d = row["occurred"]
        date_str = d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)[:10]
        p_del = delivery_map.setdefault(p_id, {})
        p_del[date_str] = p_del.get(date_str, 0) + int(row["quantity"])
    return delivery_map


def deduplicate_products(products):
    seen = {}
    for row in products:
        if int(row.get("supplier_id") or 0) == ASSEMBLED_SUPPLIER_ID:
            continue
        p_id = int(row["product_id"])
        lead = int(row.get("lead_time") or 99)
        if p_id not in seen or lead < int(seen[p_id].get("lead_time") or 99):
            seen[p_id] = row
    return list(seen.values())


def parse_archetype(name):
    if not name or "(" not in name or ")" not in name:
        return "stable"
    t = name[name.index("(") + 1 : name.rindex(")")].strip()
    if "Stockout Prone" in t:
        return "stockout_prone"
    if "Seasonal" in t and "Summer" in t:
        return "seasonal_summer"
    if "Seasonal" in t and ("Winter" in t or "Holiday" in t):
        return "seasonal_winter"
    if "Negative Trend" in t:
        return "trend_down"
    if "Positive Trend" in t:
        return "trend_up"
    if "Step Change" in t and "Up" in t:
        return "step_up"
    if "Step Change" in t and "Down" in t:
        return "step_down"
    if "New Launch" in t:
        return "new_launch"
    if "Obsolete" in t or "Dead" in t:
        return "obsolete"
    if "Lumpy" in t or "Sporadic" in t:
        return "lumpy"
    if "Outlier" in t or "Influencer" in t:
        return "outlier"
    if "Container Filler" in t:
        return "container_filler"
    if "Micro-Seasonality" in t:
        return "micro_seasonal"
    return "stable"


def simulate_one_product(product_row, sales_map, del_map, today):
    p_id = int(product_row["product_id"])
    product_uuid = str(product_row["product_uuid"])
    webshop_uuid = str(product_row["webshop_uuid"])
    lead_time = int(product_row["lead_time"] or 14)
    reorder_period = int(product_row["reorder_period"] or 30)
    starting_stock = int(product_row["starting_stock"] or 0)
    archetype = parse_archetype(product_row.get("product_name") or "")

    start_date = today - timedelta(days=365)
    total_sold = sum(sales_map.values())
    avg_daily = max(1, total_sold // max(len(sales_map), 1))
    reorder_qty = max(1, int(avg_daily * reorder_period))

    # Starting stock
    if archetype == "new_launch":
        sim_stock = 0
    elif archetype == "obsolete":
        sim_stock = starting_stock + int(avg_daily * 90)
    elif archetype == "container_filler":
        sim_stock = starting_stock + int(avg_daily * lead_time * 4)
    else:
        sim_stock = starting_stock + int(avg_daily * lead_time * 2)

    # Find launch day for new_launch
    launch_day = 0
    if archetype == "new_launch":
        for d in range(366):
            ds = (start_date + timedelta(days=d)).strftime("%Y-%m-%d")
            if sales_map.get(ds, 0) > 0:
                launch_day = d
                break

    pending = []  # list of [delivery_day, qty]
    stock_rows = []
    stockout_count = 0
    in_stockout = False
    rop_boost = False
    last_reorder = -999
    # Stockout Prone: ensure at least one stockout visible in the last 3 months (days 276–365)
    LAST_3M_START = 276
    had_stockout_in_last_3m = False
    # Pick a day in the last 3 months to force stock to 0 (so the stock graph shows a clear dip)
    force_stockout_day = 300 if archetype == "stockout_prone" else -1  # ~1 month before "today"

    for day in range(366):
        curr_date = start_date + timedelta(days=day)
        date_str = curr_date.strftime("%Y-%m-%d")
        m = curr_date.month

        # New launch: zero before launch day
        if archetype == "new_launch" and day < launch_day:
            stock_rows.append({
                "product_id": p_id,
                "product_uuid": product_uuid,
                "webshop_id": 1380,
                "webshop_uuid": webshop_uuid,
                "on_hand": 0,
                "date": date_str + " 00:00:02",
            })
            continue

        if archetype == "new_launch" and day == launch_day:
            sim_stock = max(starting_stock, int(avg_daily * reorder_period * 2))

        # (a) Actual deliveries from DB
        actual = del_map.get(date_str, 0)
        sim_stock += actual

        # (b) Simulated pending deliveries (orders we placed in-sim that arrive today)
        new_pending = []
        for entry in pending:
            if entry[0] <= day:
                sim_stock += entry[1]
            else:
                new_pending.append(entry)
        pending = new_pending

        # (c) Sales
        units_sold = sales_map.get(date_str, 0)
        sold = min(units_sold, sim_stock)
        sim_stock -= sold

        # (d) Small noise
        if archetype not in ("obsolete", "new_launch") and sim_stock > 2:
            sim_stock = max(0, sim_stock + random.randint(-1, 1))

        # (e) Stockout tracking
        if sim_stock == 0 and sold < units_sold:
            if day >= LAST_3M_START:
                had_stockout_in_last_3m = True
            if not in_stockout and random.random() < 0.70:
                stockout_count += 1
                in_stockout = True
            if archetype not in ("stockout_prone", "obsolete", "lumpy") and stockout_count >= 2 and not rop_boost:
                rop_boost = True
        else:
            in_stockout = False

        # (f) ROP
        if archetype == "stockout_prone":
            rop = int(lead_time * avg_daily * 0.6)
        elif archetype == "obsolete":
            rop = -9999 if day > 305 else 0
        elif archetype == "container_filler":
            rop = int(lead_time * avg_daily * 3.0)
        elif archetype in ("seasonal_summer",) and m in (5, 6, 7):
            rop = int(lead_time * avg_daily * 2.5)
        elif archetype in ("seasonal_winter",) and m in (10, 11, 12):
            rop = int(lead_time * avg_daily * 2.5)
        elif archetype == "micro_seasonal" and m in (2, 3, 8, 9):
            rop = int(lead_time * avg_daily * 2.0)
        elif archetype in ("step_up", "trend_up"):
            rop = int(lead_time * avg_daily * (1.8 if day < 180 else 2.5))
        elif archetype in ("step_down", "trend_down"):
            rop = int(lead_time * avg_daily * (1.5 if day < 180 else 0.8))
        else:
            rop = int(lead_time * avg_daily * 1.5)

        if rop_boost:
            rop += int(7 * avg_daily)

        # (g) Reorder if needed
        # Stockout Prone: in last 3 months, skip reorders until we've had at least one stockout (so we guarantee one)
        skip_reorder = (
            archetype == "stockout_prone"
            and day >= LAST_3M_START
            and not had_stockout_in_last_3m
        )
        incoming = sum(e[1] for e in pending)
        if not skip_reorder and (sim_stock + incoming) < rop and (day - last_reorder) >= reorder_period:
            actual_lead = max(1, lead_time + random.randint(-2, 3))
            pending.append([day + actual_lead, reorder_qty])
            last_reorder = day

        # Stockout Prone: force one day in the last 3 months to 0 so the stock graph clearly shows a stockout
        if force_stockout_day >= 0 and day == force_stockout_day:
            sim_stock = 0
            had_stockout_in_last_3m = True

        stock_rows.append({
            "product_id": p_id,
            "product_uuid": product_uuid,
            "webshop_id": 1380,
            "webshop_uuid": webshop_uuid,
            "on_hand": int(sim_stock),
            "date": date_str + " 00:00:02",
        })

    return stock_rows


# --- Entry point ---
products = fetch_product_meta.data
daily_sales = fetch_daily_sales.data
bo_data = fetch_bo_data.data if hasattr(fetch_bo_data, "data") else []
delivery_data = fetch_deliveries.data if hasattr(fetch_deliveries, "data") else []

if not isinstance(products, list):
    products = []
if not isinstance(daily_sales, list):
    daily_sales = []
if not isinstance(bo_data, list):
    bo_data = []
if not isinstance(delivery_data, list):
    delivery_data = []

products = deduplicate_products(products)
sales_map = build_sales_map(daily_sales)
delivery_map = build_delivery_map(bo_data, delivery_data)
today = datetime.utcnow().date()

all_stocks = []
for product_row in products:
    p_id = int(product_row["product_id"])
    rows = simulate_one_product(
        product_row,
        sales_map.get(p_id, {}),
        delivery_map.get(p_id, {}),
        today,
    )
    all_stocks.extend(rows)

return {"stocks": all_stocks, "product_count": len(products), "stock_rows": len(all_stocks)}

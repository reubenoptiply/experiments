"""
Retool Python block: pure-Python simulation (no numpy/pandas).
Paste this into a Retool Workflow Python block named `simulate_all_products`.

Input: fetch_products.data — list of dicts with:
  product_id, product_uuid, webshop_id, webshop_uuid, name,
  selling_price, purchase_price, supplier_id, supplier_uuid, delivery_time

Output: { "stocks": [ { product_id, product_uuid, webshop_id, webshop_uuid, on_hand, date } ] }
  date format: "YYYY-MM-DD 00:00:02"
"""
import math
import random
from datetime import datetime, timedelta


def get_base_demand(selling_price):
    if selling_price < 15:
        return 25
    if selling_price < 50:
        return 12
    return 5


def get_daily_demand(day_idx, scenario, base_qty, history_days):
    qty = 0.0
    if scenario == "Stable Fast":
        qty = base_qty * 1.5
    elif scenario == "Stable Slow":
        qty = base_qty * 0.5
    elif scenario == "Positive Trend":
        start_day = history_days - 120
        if day_idx < start_day:
            qty = base_qty
        else:
            progress = (day_idx - start_day) / 120
            qty = base_qty * (1 + (2.0 * progress))
    elif scenario == "Negative Trend":
        start_day = history_days - 120
        high_base = base_qty * 2.0
        if day_idx < start_day:
            qty = high_base
        else:
            progress = (day_idx - start_day) / 120
            qty = max(0, high_base * (1 - (0.8 * progress)))
    elif "Seasonal" in scenario:
        peak = 170
        width = 30
        if "Winter" in scenario:
            peak = 15
        if "Holiday" in scenario:
            peak = 330
            width = 5
        factor = 3.0 * math.exp(-((day_idx - peak) ** 2) / (2 * width ** 2))
        if "Winter" in scenario:
            factor = max(factor, 3.0 * math.exp(-((day_idx - 355) ** 2) / (2 * 20 ** 2)))
        if "Micro" in scenario:
            factor = factor * (1.0 if (day_idx % 30) < 5 else 0.0)
        qty = base_qty + (base_qty * factor)
    elif "Stockout" in scenario:
        qty = base_qty * 2.0
    elif "Obsolete" in scenario:
        qty = base_qty if day_idx < (history_days - 60) else 0
    elif "Outlier" in scenario:
        is_recent = day_idx > (history_days - 90)
        if is_recent and random.random() > 0.97:
            qty = base_qty * 8.0
        else:
            qty = base_qty
    elif "New Launch" in scenario:
        launch_day = history_days - 30
        if day_idx < launch_day:
            qty = 0
        else:
            boost = 2.5 if "Success" in scenario else 0.5
            qty = base_qty * boost
    elif "Container" in scenario:
        qty = base_qty * 4.0
    elif "Multi-Supplier" in scenario:
        qty = base_qty * 1.5
    elif "Sporadic" in scenario:
        qty = 3 if random.random() > 0.92 else 0
    elif "Lumpy" in scenario:
        qty = random.uniform(50, 200) if random.random() > 0.97 else 0
    elif "Step Change" in scenario:
        level = 1.0
        step_day = 200
        if "Up" in scenario and day_idx > step_day:
            level = 2.5
        if "Down" in scenario and day_idx > step_day:
            level = 0.5
        qty = base_qty * level
    else:
        qty = base_qty

    if qty > 0:
        vol = random.uniform(0.85, 1.15)
        qty = qty * vol
        if "Sporadic" not in scenario and "Lumpy" not in scenario:
            qty += random.gauss(0, 1.0)
    return int(max(0, round(qty)))


def parse_scenario_from_name(name):
    if not name or "(" not in name or ")" not in name:
        return "Stable Fast"
    start = name.index("(") + 1
    end = name.index(")", start)
    return name[start:end].strip()


def simulate_one_product(product_row, history_days, start_date):
    """Run 365-day loop for one product. Returns list of stock rows."""
    p_id = product_row.get("product_id") or product_row.get("id")
    product_uuid = product_row.get("product_uuid") or ""
    w_id = product_row.get("webshop_id")
    webshop_uuid = product_row.get("webshop_uuid") or ""
    name = product_row.get("name") or ""
    selling_price = float(product_row.get("selling_price") or 0)
    purchase_price = float(product_row.get("purchase_price") or 0)
    supplier_id = product_row.get("supplier_id")
    delivery_time = int(product_row.get("delivery_time") or 14)

    scenario = parse_scenario_from_name(name)
    base_qty = get_base_demand(selling_price)
    avg_daily = base_qty
    if "Fast" in scenario or "Container" in scenario:
        avg_daily *= 2.0
    if "Seasonal" in scenario:
        avg_daily *= 1.5
    if "Trend" in scenario:
        avg_daily *= 1.5

    reorder_point = delivery_time * avg_daily * 1.5

    sim_stock = 800
    if "New Launch" in scenario:
        sim_stock = 0
    if "Obsolete" in scenario:
        sim_stock = 600
    if "Sporadic" in scenario or "Lumpy" in scenario:
        sim_stock = 60

    pending_deliveries = []
    stock_rows = []

    for day in range(history_days):
        curr_date = start_date + timedelta(days=day)
        date_str = curr_date.strftime("%Y-%m-%d 00:00:02")

        active_rop = reorder_point
        if "Seasonal" in scenario:
            peak = 170
            if "Winter" in scenario:
                peak = 15
            if "Holiday" in scenario:
                peak = 330
            days_before_peak = peak - day
            if 0 <= days_before_peak <= 60:
                active_rop = delivery_time * avg_daily * 2.5
        if "Stockout" in scenario and day > (history_days - 90):
            active_rop = (delivery_time * avg_daily) * 0.8
        if "Obsolete" in scenario and day > (history_days - 60):
            active_rop = -9999

        arrived = 0
        new_pending = []
        for d_day, d_qty in pending_deliveries:
            if day >= d_day:
                arrived += d_qty
            else:
                new_pending.append((d_day, d_qty))
        pending_deliveries = new_pending
        sim_stock += arrived

        demand = get_daily_demand(day, scenario, base_qty, history_days)
        if "New Launch" in scenario and day == (history_days - 30):
            sim_stock += int(avg_daily * 45)

        sold = min(demand, max(0, sim_stock))
        sim_stock = max(0, sim_stock - sold)

        incoming = sum(q for _, q in pending_deliveries)
        if (sim_stock + incoming) < active_rop:
            order_q = max(10, int(avg_daily * (delivery_time + 45)))
            if "Container" in scenario:
                order_q = max(order_q, 2000)
            if "Sporadic" in scenario:
                order_q = 20
            actual_lead = delivery_time
            if "Multi-Supplier" in scenario and random.random() > 0.7:
                actual_lead = random.randint(25, 45)
            delivery_day = day + actual_lead
            pending_deliveries.append((delivery_day, order_q))

        stock_rows.append({
            "product_id": p_id,
            "product_uuid": product_uuid,
            "webshop_id": w_id,
            "webshop_uuid": webshop_uuid,
            "on_hand": int(sim_stock),
            "date": date_str,
        })

    return stock_rows


# --- Retool entry: input is fetch_products.data ---
products = fetch_products.data if fetch_products and getattr(fetch_products, "data", None) else []
if not isinstance(products, list):
    products = []

history_days = 365
end_date = datetime.utcnow()
start_date = end_date - timedelta(days=history_days)

stocks = []
for row in products:
    stocks.extend(simulate_one_product(row, history_days, start_date))

return {"stocks": stocks}

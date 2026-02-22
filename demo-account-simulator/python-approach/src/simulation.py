"""
Supply chain simulation: demand archetypes and daily stock/sales/PO loop.
Date formats (spec §5): API payloads use ISO8601 (YYYY-MM-DDTHH:MM:SSZ); SQL/DB use YYYY-MM-DD.
"""
import pandas as pd
import numpy as np
import uuid
from datetime import datetime, timedelta
import random
from typing import List, Dict, Any, Optional

class DemandEngine:
    @staticmethod
    def get_base_demand(selling_price: float) -> int:
        """Determines base velocity based on price bracket."""
        if selling_price < 15: return 25  # Fast
        elif selling_price < 50: return 12 # Medium
        return 5 # Slow

    @staticmethod
    def get_daily_demand(day_idx: int, scenario: str, base_qty: float, history_days: int) -> int:
        qty = 0.0
        
        # --- SCENARIO SHAPES ---
        if scenario == "Stable Fast":
            qty = base_qty * 1.5
        elif scenario == "Stable Slow":
            qty = base_qty * 0.5
        
        elif scenario == "Positive Trend":
            # Ramp up in the last 4 months (Day 240+)
            start_day = history_days - 120
            if day_idx < start_day:
                qty = base_qty
            else:
                # 1x -> 3x Growth
                progress = (day_idx - start_day) / 120
                qty = base_qty * (1 + (2.0 * progress))
                
        elif scenario == "Negative Trend":
            # Drop off in the last 4 months
            start_day = history_days - 120
            high_base = base_qty * 2.0
            if day_idx < start_day:
                qty = high_base
            else:
                # 100% -> 20% Decay
                progress = (day_idx - start_day) / 120
                qty = max(0, high_base * (1 - (0.8 * progress)))

        elif "Seasonal" in scenario:
            # Gaussian peak: qty = base + (base * 3 * exp(-(day-peak)^2 / (2 * width^2)))
            peak = 170 # Summer
            width = 30
            if "Winter" in scenario: peak = 15
            if "Holiday" in scenario: peak = 330; width = 5
            
            factor = 3.0 * np.exp(-((day_idx - peak)**2) / (2 * width**2))
            
            if "Winter" in scenario:  # Dec Peak
                factor = max(factor, 3.0 * np.exp(-((day_idx - 355)**2) / (2 * 20**2)))
            if "Micro" in scenario:  # Monthly payday: modulate seasonal by payday (don't overwrite)
                factor = factor * (1.0 if (day_idx % 30) < 5 else 0.0)
            qty = base_qty + (base_qty * factor)

        elif "Stockout" in scenario:
            qty = base_qty * 2.0 # High demand side of stockout prone
        
        elif "Obsolete" in scenario:
            # Stop selling 60 days ago
            qty = base_qty if day_idx < (history_days - 60) else 0
            
        elif "Outlier" in scenario:
            # 3% huge spikes in last 90 days
            is_recent = day_idx > (history_days - 90)
            if is_recent and random.random() > 0.97: 
                qty = base_qty * 8.0 # Massive spike
            else: 
                qty = base_qty

        elif "New Launch" in scenario:
            # STRICT 30 DAYS AGO LAUNCH
            launch_day = history_days - 30
            if day_idx < launch_day:
                qty = 0
            else:
                # Launch Boost: Success (2.5x) or Flop (0.5x)
                boost = 2.5 if "Success" in scenario else 0.5
                qty = base_qty * boost

        elif "Container" in scenario: 
            qty = base_qty * 4.0
            
        elif "Multi-Supplier" in scenario: 
            qty = base_qty * 1.5
        
        elif "Sporadic" in scenario:
            qty = 3 if random.random() > 0.92 else 0 # Sparse (Poisson-ish)
            
        elif "Lumpy" in scenario:
            qty = random.uniform(50, 200) if random.random() > 0.97 else 0 # Bulk B2B
            
        elif "Step Change" in scenario:
            # Jump at Day 200
            level = 1.0
            step_day = 200
            if "Up" in scenario and day_idx > step_day: level = 2.5
            if "Down" in scenario and day_idx > step_day: level = 0.5
            qty = base_qty * level
            
        else: 
            qty = base_qty

        # --- NOISE (Tuned for Readability) ---
        if qty > 0:
            # Lower volatility (±15%) to make patterns clearer
            vol = random.uniform(0.85, 1.15)
            qty = qty * vol
            
            # Additive noise (only if not sporadic or lumpy)
            if "Sporadic" not in scenario and "Lumpy" not in scenario:
                qty += np.random.normal(0, 1.0)
                
        return int(max(0, round(qty)))

class SupplyChainSimulator:
    def __init__(self, history_days: int = 365):
        self.history_days = history_days
        self.start_date = datetime.now() - timedelta(days=history_days)
        self.demand_engine = DemandEngine()

    def simulate_product(self, product_data: Dict[str, Any], scenario: str) -> Dict[str, Any]:
        p_id = product_data['id']
        p_sku = product_data['sku']
        supplier_id = product_data['supplier_id']
        w_id = product_data['shop_id']
        
        selling_price = float(product_data.get('selling_price', 0) or 0)
        purchase_price = float(product_data.get('purchase_price', 0) or 0)
        current_stock = int(product_data.get('current_stock_on_hand', 0) or 0)
        lead_time = int(product_data.get('product_delivery_time', 14))

        # Logistics Parameters
        base_qty = self.demand_engine.get_base_demand(selling_price)
        avg_daily = base_qty
        
        # Scenario adjustments for ROP
        if "Fast" in scenario or "Container" in scenario: avg_daily *= 2.0
        if "Seasonal" in scenario: avg_daily *= 1.5
        if "Trend" in scenario: avg_daily *= 1.5 
        
        reorder_point = lead_time * avg_daily * 1.5 # 1.5x Lead Time Demand
        
        # Initial Stock calculation
        sim_stock = current_stock + 800 
        if "New Launch" in scenario: sim_stock = 0
        if "Obsolete" in scenario: sim_stock = 600
        if "Sporadic" in scenario or "Lumpy" in scenario: sim_stock = 60
        
        pending_deliveries = []
        sales_history = []
        buy_orders = []
        stock_history = []
        
        missed_sales_days = 0
        total_sales = 0

        for day in range(self.history_days):
            curr_date = self.start_date + timedelta(days=day)
            date_str = curr_date.strftime("%Y-%m-%d")
            iso_date = curr_date.strftime("%Y-%m-%dT12:00:00Z")
            
            # --- SABOTAGE / ADJUSTMENTS ---
            active_rop = reorder_point
            if "Stockout" in scenario and day > (self.history_days - 90):
                 # Supply-side sabotage: Cut ROP to 80% of LTD (guarantees stockout)
                 active_rop = (lead_time * avg_daily) * 0.8
            
            if "Obsolete" in scenario and day > (self.history_days - 60):
                 active_rop = -9999 # Stop ordering

            # A. INBOUND (Deliveries)
            arrived = 0
            new_pending = []
            for d_day, d_qty, bo_data in pending_deliveries:
                if day >= d_day:
                    arrived += d_qty
                    # Mark BO as received if needed in your logic
                else:
                    new_pending.append((d_day, d_qty, bo_data))
            pending_deliveries = new_pending
            sim_stock += arrived

            # B. SALES (Outbound)
            demand = self.demand_engine.get_daily_demand(day, scenario, base_qty, self.history_days)
            
            # Injection for New Launch
            if "New Launch" in scenario and day == (self.history_days - 30):
                sim_stock += int(avg_daily * 45) # 1.5 months initial stock
                
            sold = demand
            if demand > sim_stock:
                missed_sales_days += 1
                sold = max(0, sim_stock)
            
            sim_stock -= sold 
            total_sales += sold
            
            if sold > 0:
                sales_history.append({
                    "product_id": p_id,
                    "sku_id": p_sku,
                    "quantity": sold,
                    "price": selling_price,
                    "date": date_str,
                    "iso_date": iso_date
                })

            # C. REORDER (ROP Check)
            incoming = sum([x[1] for x in pending_deliveries])
            if (sim_stock + incoming) < active_rop:
                order_q = int(avg_daily * (lead_time + 45)) # Order 45 days of coverage
                if "Container" in scenario: order_q = max(order_q, 2000)
                if "Sporadic" in scenario: order_q = 20
                order_q = max(10, order_q)
                
                # Lead Time Variance
                actual_lead = lead_time
                if "Multi-Supplier" in scenario and random.random() > 0.7:
                    actual_lead = random.randint(25, 45)
                
                delivery_day = day + actual_lead
                expected_date = (self.start_date + timedelta(days=delivery_day)).strftime("%Y-%m-%dT12:00:00Z")
                
                buy_order = {
                    "supplier_id": supplier_id,
                    "product_id": p_id,
                    "placed": iso_date,
                    "expected_delivery": expected_date,
                    "quantity": order_q,
                    "unit_cost": purchase_price,
                    "total_value": round(order_q * purchase_price, 2)
                }
                buy_orders.append(buy_order)
                pending_deliveries.append((delivery_day, order_q, buy_order))

            # D. SNAPSHOT
            stock_history.append({
                "product_id": p_id,
                "webshop_id": w_id,
                "on_hand": max(0, sim_stock),
                "date": date_str
            })

        return {
            "sales": sales_history,
            "buy_orders": buy_orders,
            "stocks": stock_history,
            "metrics": {
                "missed_sales_days": missed_sales_days,
                "total_sales": total_sales,
                "scenario": scenario
            }
        }

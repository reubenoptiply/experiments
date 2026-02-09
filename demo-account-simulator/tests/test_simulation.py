"""Unit tests for DemandEngine and SupplyChainSimulator."""
import random
import numpy as np
import pytest
from src.simulation import DemandEngine, SupplyChainSimulator


class TestDemandEngine:
    """Tests for DemandEngine.get_base_demand and get_daily_demand."""

    def test_get_base_demand_fast(self):
        assert DemandEngine.get_base_demand(10.0) == 25
        assert DemandEngine.get_base_demand(14.99) == 25

    def test_get_base_demand_medium(self):
        assert DemandEngine.get_base_demand(15.0) == 12
        assert DemandEngine.get_base_demand(49.99) == 12

    def test_get_base_demand_slow(self):
        assert DemandEngine.get_base_demand(50.0) == 5
        assert DemandEngine.get_base_demand(100.0) == 5

    def test_get_daily_demand_stable_fast(self):
        random.seed(42)
        np.random.seed(42)
        base = 25
        history_days = 365
        # Stable Fast: qty = base * 1.5 ± noise, so expect positive and in reasonable range
        qty = DemandEngine.get_daily_demand(100, "Stable Fast", base, history_days)
        assert qty >= 0
        assert 20 <= qty <= 60  # 1.5 * 25 = 37.5 ± 15% + small noise

    def test_get_daily_demand_stable_slow(self):
        random.seed(42)
        np.random.seed(42)
        base = 25
        history_days = 365
        qty = DemandEngine.get_daily_demand(100, "Stable Slow", base, history_days)
        assert qty >= 0
        assert qty <= 25  # 0.5 * 25 = 12.5 + noise

    def test_get_daily_demand_obsolete_before_cutoff(self):
        random.seed(42)
        np.random.seed(42)
        base = 25
        history_days = 365
        # Before cutoff (day 305): demand exists
        qty = DemandEngine.get_daily_demand(300, "Obsolete", base, history_days)
        assert qty >= 0

    def test_get_daily_demand_obsolete_after_cutoff(self):
        base = 25
        history_days = 365
        # After cutoff: 0 demand
        qty = DemandEngine.get_daily_demand(310, "Obsolete", base, history_days)
        assert qty == 0

    def test_get_daily_demand_new_launch_before_launch(self):
        base = 25
        history_days = 365
        launch_day = history_days - 30  # 335
        qty = DemandEngine.get_daily_demand(334, "New Launch Success", base, history_days)
        assert qty == 0

    def test_get_daily_demand_new_launch_after_launch(self):
        random.seed(42)
        np.random.seed(42)
        base = 25
        history_days = 365
        qty = DemandEngine.get_daily_demand(336, "New Launch Success", base, history_days)
        assert qty >= 0  # 2.5 * base with noise

    def test_get_daily_demand_seasonal_summer(self):
        random.seed(42)
        np.random.seed(42)
        base = 12
        history_days = 365
        # Peak at day 170 for Summer
        qty = DemandEngine.get_daily_demand(170, "Seasonal Summer", base, history_days)
        assert qty >= 0
        assert qty >= base  # At peak, demand is base + (base * factor)


class TestSupplyChainSimulator:
    """Tests for SupplyChainSimulator.simulate_product."""

    @pytest.fixture
    def product_data(self):
        return {
            "id": 28666283,
            "sku": "SKU-DEMO-1",
            "name": "Product (Stable Fast)",
            "shop_id": 1380,
            "supplier_id": 1001,
            "selling_price": 20.0,
            "purchase_price": 10.0,
            "current_stock_on_hand": 50,
            "product_delivery_time": 14,
        }

    def test_simulate_product_returns_required_keys(self, product_data):
        sim = SupplyChainSimulator(history_days=5)
        result = sim.simulate_product(product_data, "Stable Fast")
        assert "stocks" in result
        assert "sales" in result
        assert "buy_orders" in result
        assert "metrics" in result

    def test_simulate_product_stocks_structure(self, product_data):
        sim = SupplyChainSimulator(history_days=5)
        result = sim.simulate_product(product_data, "Stable Fast")
        assert len(result["stocks"]) == 5
        for row in result["stocks"]:
            assert "product_id" in row
            assert "webshop_id" in row
            assert "on_hand" in row
            assert "date" in row
            assert row["product_id"] == 28666283
            assert row["webshop_id"] == 1380

    def test_simulate_product_buy_orders_contain_supplier_id(self, product_data):
        sim = SupplyChainSimulator(history_days=30)  # Enough days to trigger at least one order
        result = sim.simulate_product(product_data, "Stable Fast")
        assert "buy_orders" in result
        for bo in result["buy_orders"]:
            assert "supplier_id" in bo
            assert bo["supplier_id"] == 1001
            assert bo["product_id"] == 28666283

    def test_simulate_product_sales_structure(self, product_data):
        sim = SupplyChainSimulator(history_days=5)
        result = sim.simulate_product(product_data, "Stable Fast")
        for sale in result["sales"]:
            assert "product_id" in sale
            assert "quantity" in sale
            assert "date" in sale
            assert "iso_date" in sale

    def test_simulate_product_metrics(self, product_data):
        sim = SupplyChainSimulator(history_days=5)
        result = sim.simulate_product(product_data, "Stable Fast")
        assert "scenario" in result["metrics"]
        assert result["metrics"]["scenario"] == "Stable Fast"
        assert "total_sales" in result["metrics"]
        assert "missed_sales_days" in result["metrics"]

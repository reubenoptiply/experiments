import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging
from src.simulation import SupplyChainSimulator
from src.database import DatabaseManager

# Setup logging for Traycer/Cloud Run observability
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Fail fast at startup when FAIL_FAST_NO_DB=1 and DATABASE_URL is missing (e.g. Cloud Run)."""
    if os.getenv("FAIL_FAST_NO_DB") == "1" and not os.getenv("DATABASE_URL"):
        raise RuntimeError("FAIL_FAST_NO_DB=1 but DATABASE_URL is not set. Set DATABASE_URL or unset FAIL_FAST_NO_DB.")
    yield

app = FastAPI(title="Shop 1380 Inventory Simulation Engine", lifespan=lifespan)
db = DatabaseManager()

# Product ID whitelist for demo shop 1380 (from spec §5). Only these products may be simulated.
DEMO_PRODUCT_WHITELIST = frozenset([
    28666283, 28666286, 28666287, 28666288, 28666289, 28666290, 28666291, 28666292,
    28666293, 28666294, 28666295, 28666296, 28666297, 28666298, 28666299, 28666300,
    28666301, 28666302, 28666303, 28666304, 28666305, 28666306, 28666307, 28666308,
    28666309, 28666310, 28666311, 28666312, 28666313, 28666314, 28666315, 28666316,
])

class ProductInput(BaseModel):
    id: int
    sku: str
    name: str
    shop_id: int
    supplier_id: int
    selling_price: Optional[float] = 0.0
    purchase_price: Optional[float] = 0.0
    current_stock_on_hand: Optional[int] = 0
    product_delivery_time: Optional[int] = 14

class SimulationRequest(BaseModel):
    webshop_id: int
    products: List[ProductInput]

@app.get("/")
async def root():
    return {"status": "active", "shop": 1380}


@app.get("/health")
async def health():
    """Check database connectivity. Returns 503 if DB not configured or unreachable."""
    if not db.engine:
        return JSONResponse(
            content={"status": "unhealthy", "detail": "DATABASE_URL not set"},
            status_code=503,
        )
    if not db.check_connection():
        return JSONResponse(
            content={"status": "unhealthy", "detail": "Database unreachable"},
            status_code=503,
        )
    return {"status": "healthy"}

@app.post("/simulate")
async def run_simulation(request: SimulationRequest, background_tasks: BackgroundTasks):
    """
    Triggers Phase A: The Creator.
    Wipes history and generates new 365-day synthetic data.
    """
    if request.webshop_id != 1380:
        raise HTTPException(status_code=403, detail="Unauthorized Shop ID")
    if not db.engine:
        raise HTTPException(status_code=503, detail="Database not configured (DATABASE_URL not set).")

    # 1. Filter to whitelisted products only (spec §5)
    products_to_run = [p for p in request.products if p.id in DEMO_PRODUCT_WHITELIST]
    skipped = [p.id for p in request.products if p.id not in DEMO_PRODUCT_WHITELIST]
    if skipped:
        logger.warning(f"Skipping non-whitelisted product IDs: {skipped}")
    if not products_to_run:
        raise HTTPException(
            status_code=400,
            detail="No whitelisted products in request. Only product IDs in the demo whitelist may be simulated."
        )

    # 2. Parse Archetypes from names
    def get_scenario(name: str) -> str:
        if "(" in name and ")" in name:
            return name.split("(")[1].split(")")[0]
        return "Stable Fast"

    # 3. Run simulation in memory first (no partial state if DB fails)
    simulator = SupplyChainSimulator()
    all_stocks = []
    all_sales = []
    all_buy_orders = []
    try:
        for p in products_to_run:
            scenario = get_scenario(p.name)
            results = simulator.simulate_product(p.model_dump(), scenario)
            all_stocks.extend(results['stocks'])
            all_sales.extend(results['sales'])
            all_buy_orders.extend(results['buy_orders'])
    except Exception as e:
        logger.exception("Simulation failed")
        raise HTTPException(status_code=500, detail=f"Simulation failed: {e!s}") from e

    # 4. Single transaction: wipe then insert (avoids wipe-without-insert on failure)
    try:
        logger.info(f"Wiping and inserting {len(all_stocks)} stock records for shop 1380")
        db.wipe_and_insert_stocks(request.webshop_id, all_stocks)
    except Exception as e:
        logger.exception("Database wipe/insert failed")
        raise HTTPException(status_code=500, detail=f"Database update failed: {e!s}") from e

    # Retool/caller should POST api_payloads to Optiply Public API in batches with delay to respect rate limits (spec §5).
    return {
        "message": "Simulation complete",
        "record_counts": {
            "stocks": len(all_stocks),
            "sales": len(all_sales),
            "buy_orders": len(all_buy_orders)
        },
        "api_payloads": {
            "sales": all_sales,
            "buy_orders": all_buy_orders
        },
        "note": "POST api_payloads.sales and api_payloads.buy_orders to Optiply Public API in batches with delay (e.g. 100–200ms between requests) to respect rate limits.",
    }

@app.post("/maintain")
async def run_maintenance(webshop_id: int = Query(..., description="Webshop ID (must be 1380 for demo)")):
    """
    Triggers Phase B: The Maintainer.
    Shifts all dates forward to today.
    """
    if webshop_id != 1380:
        raise HTTPException(status_code=403, detail="Unauthorized Shop ID")
    if not db.engine:
        raise HTTPException(status_code=503, detail="Database not configured (DATABASE_URL not set).")
    try:
        db.run_maintenance_shift(webshop_id)
    except Exception as e:
        logger.exception("Maintenance shift failed")
        raise HTTPException(status_code=500, detail=f"Maintenance failed: {e!s}") from e
    return {"status": "Maintenance complete", "shop": webshop_id}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

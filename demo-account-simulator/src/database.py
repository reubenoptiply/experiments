import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL") # Format: postgresql://user:password@host:port/dbname

class DatabaseManager:
    def __init__(self):
        if not DATABASE_URL:
            # Fallback for local development if not provided, but in production this should be set
            self.engine = None
            print("Warning: DATABASE_URL not set. Database operations will fail.")
        else:
            self.engine = create_engine(DATABASE_URL)
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def check_connection(self) -> bool:
        """Return True if database is configured and reachable."""
        if not self.engine:
            return False
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    def wipe_stocks(self, webshop_id: int):
        """Soft delete stocks for the demo shop."""
        if not self.engine: return
        with self.engine.connect() as conn:
            conn.execute(
                text("UPDATE stocks SET deleted_at = NOW() WHERE webshop_id = :shop_id AND deleted_at IS NULL"),
                {"shop_id": webshop_id}
            )
            conn.commit()

    def batch_insert_stocks(self, stocks_data: List[Dict[str, Any]], batch_size: int = 2000):
        """Efficiently inserts stock snapshots with ON CONFLICT resolution."""
        if not self.engine or not stocks_data: return
        
        # Assumes stocks has unique constraint on (product_id, date). If schema uses (product_id, webshop_id, date), add webshop_id to ON CONFLICT.
        query = """
        INSERT INTO stocks (product_id, webshop_id, on_hand, date)
        VALUES (:product_id, :webshop_id, :on_hand, :date)
        ON CONFLICT (product_id, date)
        DO UPDATE SET on_hand = EXCLUDED.on_hand, deleted_at = NULL;
        """
        
        with self.engine.connect() as conn:
            for i in range(0, len(stocks_data), batch_size):
                batch = stocks_data[i : i + batch_size]
                for row in batch:
                    conn.execute(text(query), row)
            conn.commit()

    def wipe_and_insert_stocks(self, webshop_id: int, stocks_data: List[Dict[str, Any]], batch_size: int = 2000):
        """Wipe then insert in a single transaction to avoid partial state on failure."""
        if not self.engine: return
        if not stocks_data: return
        wipe_sql = text(
            "UPDATE stocks SET deleted_at = NOW() WHERE webshop_id = :shop_id AND deleted_at IS NULL"
        )
        insert_sql = text("""
        INSERT INTO stocks (product_id, webshop_id, on_hand, date)
        VALUES (:product_id, :webshop_id, :on_hand, :date)
        ON CONFLICT (product_id, date)
        DO UPDATE SET on_hand = EXCLUDED.on_hand, deleted_at = NULL;
        """)
        with self.engine.connect() as conn:
            conn.execute(wipe_sql, {"shop_id": webshop_id})
            for i in range(0, len(stocks_data), batch_size):
                for row in stocks_data[i : i + batch_size]:
                    conn.execute(insert_sql, row)
            conn.commit()

    def run_maintenance_shift(self, webshop_id: int):
        """Shifts all dates forward by the lag between latest data and today."""
        if not self.engine: return
        
        maintenance_queries = [
            # 1. Update Sell Orders (spec §4 Phase B: placed only; no completed)
            """
            WITH lag AS (SELECT (CURRENT_DATE - MAX(placed)::date) as days FROM sell_orders WHERE webshop_id = :shop_id)
            UPDATE sell_orders 
            SET placed = placed + (SELECT days FROM lag) * INTERVAL '1 day'
            WHERE webshop_id = :shop_id AND (SELECT days FROM lag) > 0;
            """,
            # 2. Update Buy Orders (spec §4 Phase B: placed and expected_delivery_date only; no completed)
            """
            WITH lag AS (SELECT (CURRENT_DATE - MAX(placed)::date) as days FROM buy_orders WHERE webshop_id = :shop_id)
            UPDATE buy_orders 
            SET placed = placed + (SELECT days FROM lag) * INTERVAL '1 day',
                expected_delivery_date = expected_delivery_date + (SELECT days FROM lag) * INTERVAL '1 day'
            WHERE webshop_id = :shop_id AND (SELECT days FROM lag) > 0;
            """,
            # 3. Update Stocks
            """
            WITH lag AS (SELECT (CURRENT_DATE - MAX(date)::date) as days FROM stocks WHERE webshop_id = :shop_id)
            UPDATE stocks 
            SET date = date + (SELECT days FROM lag) * INTERVAL '1 day'
            WHERE webshop_id = :shop_id AND (SELECT days FROM lag) > 0;
            """
        ]
        
        with self.engine.connect() as conn:
            for q in maintenance_queries:
                conn.execute(text(q), {"shop_id": webshop_id})
            conn.commit()

-- Insert simulated stock rows. build_stocks_insert.data.sql_values is the raw VALUES list.
-- Run after soft_delete_stocks.
INSERT INTO stocks (product_id, product_uuid, webshop_id, webshop_uuid, on_hand, date)
VALUES {{ build_stocks_insert.data.sql_values }};

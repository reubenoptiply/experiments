INSERT INTO stocks (product_id, product_uuid, webshop_id, webshop_uuid, on_hand, date)
SELECT t.product_id, t.product_uuid, t.webshop_id, t.webshop_uuid, t.on_hand, t.date
FROM jsonb_to_recordset(
  {{ JSON.stringify(build_stocks_insert.data.record_set) }}::jsonb
) AS t(product_id int, product_uuid uuid, webshop_id int, webshop_uuid uuid, on_hand int, date timestamp);

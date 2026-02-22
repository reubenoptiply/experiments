// Retool JS block: build_stocks_insert
// Runs after simulate_stocks. Maps simulate_stocks.data.stocks to SQL VALUES tuple string.

const stocks = simulate_stocks?.data?.stocks;

if (!stocks || !Array.isArray(stocks) || stocks.length === 0) {
  console.warn("build_stocks_insert: simulate_stocks.data.stocks is empty or undefined");
  return { sql_values: "", full_insert_sql: "", record_set: [] };
}

const valuesString = stocks
  .map((row) => {
    const product_id = row.product_id;
    const product_uuid = String(row.product_uuid).replace(/'/g, "''");
    const webshop_id = row.webshop_id;
    const webshop_uuid = String(row.webshop_uuid).replace(/'/g, "''");
    const on_hand = row.on_hand;
    const date = String(row.date).replace(/'/g, "''");
    return `(${product_id}, '${product_uuid}', ${webshop_id}, '${webshop_uuid}', ${on_hand}, '${date}')`;
  })
  .join(",\n");

// Full statement so Retool runs it as one query (avoids VALUES $1 parameterization error)
const fullInsertSql =
  "INSERT INTO stocks (product_id, product_uuid, webshop_id, webshop_uuid, on_hand, date)\nVALUES\n  " +
  valuesString;

return { sql_values: valuesString, full_insert_sql: fullInsertSql, record_set: stocks };

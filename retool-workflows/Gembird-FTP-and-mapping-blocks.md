# Gembird: FTP → Optiply (stock + cost price)

**Supplier:** Gembird (Optiply `supplier_id` **772048**)  
**FTP:** `ftp.gmb.nl` — user `AlleeninktBV`, files at **root** (no subdirs).

## File structure on FTP

| File | Purpose | Product ID | Stock | Price |
|------|--------|------------|--------|--------|
| **gmb_stock.csv** | Stock | `sku` | `qty` | — |
| **gmb_NL.csv** | Products + prices | `sku` | (also has `qty`) | `price` |

- **gmb_stock.csv** — CSV with header: `status,store,websites,attribute_Set,sku,type,qty,is_in_stock,visibility,EAN`. Use **sku** and **qty**.
- **gmb_NL.csv** — CSV with many columns; use **sku** and **price** (cost/unit price). File has quoted fields and commas inside values; use proper CSV parsing.

---

## 1. Block: Get FTP stock (Python – `craft_ftp`)

**Resource:** Run Python (e.g. query name `craft_ftp`). Connects to Gembird FTP and returns stock from **gmb_stock.csv**.

```python
from ftplib import FTP
import io
import csv

try:
    ftp = FTP('ftp.gmb.nl')
    ftp.login(user='AlleeninktBV', passwd='F7M5VM58c6VxHjFxNK')
except Exception as e:
    print(f"Connection Error: {e}")
    return []

buf = io.BytesIO()
try:
    ftp.retrbinary('RETR gmb_stock.csv', buf.write)
except Exception as e:
    print(f"Download Error: {e}")
    ftp.quit()
    return []

ftp.quit()

buf.seek(0)
text = buf.getvalue().decode('utf-8-sig', errors='replace')
reader = csv.DictReader(io.StringIO(text))
clean_data = []
for row in reader:
    sku = (row.get('sku') or '').strip()
    qty = row.get('qty', '').strip()
    if sku:
        clean_data.append({"SKU": sku, "Stock": qty})

return clean_data
```

**Output shape:** `[{ "SKU": "19A-BRUSH-02", "Stock": "147" }, ...]`

---

## 2. Block: Get FTP price (Python – `craft_price`)

**Resource:** Run Python (e.g. query name `craft_price`). Returns cost/unit price from **gmb_NL.csv** (column `price`).

```python
from ftplib import FTP
import io
import csv

try:
    ftp = FTP('ftp.gmb.nl')
    ftp.login(user='AlleeninktBV', passwd='F7M5VM58c6VxHjFxNK')
except Exception as e:
    print(f"Connection Error: {e}")
    return []

buf = io.BytesIO()
try:
    ftp.retrbinary('RETR gmb_NL.csv', buf.write)
except Exception as e:
    print(f"Download Error: {e}")
    ftp.quit()
    return []

ftp.quit()

buf.seek(0)
text = buf.getvalue().decode('utf-8-sig', errors='replace')
reader = csv.DictReader(io.StringIO(text))
clean_data = []
for row in reader:
    sku = (row.get('sku') or '').strip()
    price = (row.get('price') or '').strip()
    if sku and price:
        clean_data.append({"SKU": sku, "UnitPrice": price})

return clean_data
```

**Output shape:** `[{ "SKU": "19A-BRUSH-02", "UnitPrice": "3.48" }, ...]`

---

## 3. Block: Get Optiply data (SQL)

Query your Optiply DB for Gembird supplier products. Must return **id**, **sku**, **free_stock**, **cost_price**.

```sql
SELECT
  sp.id,
  sp.sku,
  sp.free_stock,
  sp.cost_price
FROM supplier_products sp
WHERE sp.supplier_id = 772048
  AND sp.deleted_at IS NULL
  AND sp.status = 'enabled';
```

**Resource:** Your Optiply DB (e.g. PostgreSQL). Query name e.g. `get_optiply_data`.

---

## 4. Block: Map FTP to Optiply (JavaScript – `map_suppliers`)

Same logic as Quantore: normalise data and SKUs, build stock/price lookups, output one row per product that needs a stock and/or price update. Use **after** `craft_ftp`, `craft_price`, and `get_optiply_data`.

```javascript
// Normalize: ensure we always have arrays
const toArray = (x) => Array.isArray(x) ? x : (x && x.data && Array.isArray(x.data) ? x.data : (x && x.data ? [x.data] : []));
const supplierList = toArray(craft_ftp && craft_ftp.data);
const priceList = toArray(craft_price && craft_price.data);
const optiplyArray = toArray(get_optiply_data && get_optiply_data.data);

// Normalize SKU (Gembird uses codes like 19A-BRUSH-02; trim and optional leading-zero strip)
const norm = (s) => (s == null || s === '') ? '' : String(s).trim().replace(/^0+/, '') || '0';

const optiplyLookup = {};
optiplyArray.forEach(item => {
  if (item.sku != null) {
    optiplyLookup[norm(item.sku)] = item;
  }
});

const stockBySku = {};
supplierList.forEach(item => {
  const sku = norm(item['SKU'] ?? item['sku'] ?? '');
  const stock = item['Stock'] ?? item['stock'];
  if (sku) stockBySku[sku] = stock;
});

const priceBySku = {};
priceList.forEach(p => {
  const sku = norm(p && (p.SKU ?? p.sku ?? ''));
  const price = p && (p.UnitPrice ?? p.unit_price);
  if (sku) priceBySku[sku] = price;
});

const allSkus = new Set([...Object.keys(stockBySku), ...Object.keys(priceBySku)]);

const updates = [];
allSkus.forEach(normSku => {
  const dbItem = optiplyLookup[normSku];
  if (!dbItem) return;

  const rawStock = stockBySku[normSku];
  const rawPrice = priceBySku[normSku];
  const parsedStock = rawStock != null && String(rawStock).trim() !== '' ? parseInt(rawStock, 10) : NaN;
  const parsedPrice = rawPrice != null && String(rawPrice).trim() !== '' ? parseFloat(rawPrice) : NaN;
  const newStock = Number.isNaN(parsedStock) ? null : parsedStock;
  const newPrice = Number.isNaN(parsedPrice) ? null : parsedPrice;

  const currentStock = dbItem.free_stock;
  const currentPrice = dbItem.cost_price != null ? parseFloat(dbItem.cost_price) : null;
  const needStockUpdate = newStock != null && (currentStock == null || parseInt(currentStock, 10) !== newStock);
  const needPriceUpdate = newPrice != null && (currentPrice == null || Math.abs(currentPrice - newPrice) > 1e-9);

  if (needStockUpdate || needPriceUpdate) {
    updates.push({
      id: dbItem.id,
      free_stock: needStockUpdate ? newStock : null,
      cost_price: needPriceUpdate ? newPrice : null
    });
  }
});

return updates;
```

**Output shape:** `[{ id, free_stock, cost_price }, ...]` — same as Quantore; feed the SQL below.

---

## 5. Block: Update free_stock and cost_price in DB (SQL)

Single UPDATE from `map_suppliers.data`. Only overwrites each column when the row has a non-null value.

```sql
UPDATE supplier_products AS sp
SET
  free_stock   = CASE WHEN update_data.free_stock IS NOT NULL THEN update_data.free_stock ELSE sp.free_stock END,
  cost_price   = CASE WHEN update_data.cost_price IS NOT NULL THEN update_data.cost_price ELSE sp.cost_price END,
  updated_at   = NOW()
FROM jsonb_to_recordset(
  {{ JSON.stringify(map_suppliers.data) }}::jsonb
) AS update_data(id int, free_stock int, cost_price numeric)
WHERE sp.id = update_data.id;
```

**Resource:** Same Optiply DB. Run after `map_suppliers`.

---

## Flow summary

1. **craft_ftp** — FTP `gmb_stock.csv` → `[{ SKU, Stock }]`
2. **craft_price** — FTP `gmb_NL.csv` → `[{ SKU, UnitPrice }]`
3. **get_optiply_data** — SQL `supplier_id = 772048` → `[{ id, sku, free_stock, cost_price }]`
4. **map_suppliers** — JS: normalise SKUs, compare stock/price, output `[{ id, free_stock, cost_price }]`
5. **SQL update** — one UPDATE on `supplier_products` for both `free_stock` and `cost_price`

Run 1–3 in parallel (same trigger), then 4, then 5.

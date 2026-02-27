# Quantore: FTP data block + mapping with Optiply

## 1. Product identifier match check

| Source | Field | Format | Example |
|--------|--------|--------|--------|
| **FTP** (StockV4/STOCK.XML) | `ProductCodeSupplier` | 6-digit, often zero-padded | `000450`, `009001`, `110003` |
| **Optiply** (export / supplier_products) | `sku` | 5–7 digit, some leading zeros | `091232`, `110003`, `800252`, `1385455` |

**Conclusion:** The same identifier is used on both sides (supplier product code). Matching is done by **trimmed string**:

- FTP → `SKU` (from `ProductCodeSupplier`)
- Optiply → `sku` (from `supplier_products`)

**From a typical Optiply supplier_products export:**

- 100 rows, 99 unique SKUs.
- 2 SKUs have **trailing spaces**: `800313 `, `1391808 `. The mapping block trims both sides, so these will still match if FTP sends `800313` / `1391808`.
- Many Optiply SKUs are 6-digit (e.g. `800252`, `091232`, `110003`), same style as FTP’s `ProductCodeSupplier`. As long as Quantore uses the same code in STOCK.XML as in your catalog, they will match.

---

## 2. Block: Get FTP data (Python – Retool “Run Python” / `craft_ftp`)

Use this in a **Python** query block that runs first (e.g. `craft_ftp`). It reads **StockV4/STOCK.XML** and returns a list of `{ "SKU", "Stock" }` for mapping.

```python
from ftplib import FTP
import io
import xml.etree.ElementTree as ET

# 1. Connect and Navigate
try:
    ftp = FTP('ftp.quantore.com')
    ftp.login(user='ALLCOE', passwd='FP=32Ejbh')
    ftp.cwd('StockV4')
except Exception as e:
    print(f"Connection Error: {e}")
    return []

# 2. Download STOCK.XML
download_stream = io.BytesIO()
try:
    ftp.retrbinary('RETR STOCK.XML', download_stream.write)
except Exception as e:
    print(f"Download Error: {e}")
    ftp.quit()
    return []

ftp.quit()

# 3. Parse XML
download_stream.seek(0)
content = download_stream.getvalue().decode('utf-8-sig', errors='ignore')

try:
    root = ET.fromstring(content)
except ET.ParseError as e:
    print(f"XML Parse Error: {e}")
    return []

clean_data = []

# 4. Extract Data (ProductCodeSupplier = product id, AvailableStock = stock qty)
for stock in root.findall('Stock'):
    p_code = stock.find('ProductCodeSupplier')
    p_stock = stock.find('AvailableStock')

    if p_code is not None and p_stock is not None:
        clean_data.append({
            "SKU": p_code.text.strip() if p_code.text else "",
            "Stock": p_stock.text
        })

return clean_data
```

**Output shape:** `[{ "SKU": "000450", "Stock": "22" }, ...]`  
Use this as the “supplier list” in the mapping block (e.g. `craft_ftp.data`).

---

## 3. Block: Get FTP price data (Python – `craft_price`)

Use this in a **Python** query block (e.g. `craft_price`). It reads **Price/PRICE.XML** and returns `{ "SKU", "UnitPrice" }` so the mapping block can add a **cost_price** column. Run it in parallel with `craft_ftp` (same trigger, e.g. after `workflow_data`).

```python
from ftplib import FTP
import io
import xml.etree.ElementTree as ET

try:
    ftp = FTP('ftp.quantore.com')
    ftp.login(user='ALLCOE', passwd='FP=32Ejbh')
    ftp.cwd('Price')
except Exception as e:
    print(f"Connection Error: {e}")
    return []

download_stream = io.BytesIO()
try:
    ftp.retrbinary('RETR PRICE.XML', download_stream.write)
except Exception as e:
    print(f"Download Error: {e}")
    ftp.quit()
    return []

ftp.quit()

download_stream.seek(0)
content = download_stream.getvalue().decode('utf-8-sig', errors='ignore')

try:
    root = ET.fromstring(content)
except ET.ParseError as e:
    print(f"XML Parse Error: {e}")
    return []

clean_data = []
for price in root.findall('Price'):
    p_code = price.find('ProductCodeSupplier')
    unit_price = price.find('UnitPrice')
    if p_code is not None and unit_price is not None and unit_price.text:
        clean_data.append({
            "SKU": (p_code.text or "").strip(),
            "UnitPrice": unit_price.text.strip()
        })

return clean_data
```

**Output shape:** `[{ "SKU": "000450", "UnitPrice": "24.06" }, ...]`  
Used by `map_suppliers` to fill the **cost_price** column.

---

## 4. Block: Map FTP to Optiply (JavaScript – `map_suppliers`)

Use this in a **JavaScript** query that runs after:

1. `craft_ftp` (stock from FTP; may be empty if only price feed runs)
2. `craft_price` (prices from FTP; may be empty if only stock feed runs)
3. `get_optiply_data` (Optiply supplier products: `id`, `sku`, `free_stock`, **`cost_price`**)

**Independent updates:** If the feed has only stock, only `free_stock` is updated in the DB. If only price, only `cost_price` is updated. If both, both are updated. The SQL in 5b only overwrites each column when the row has a non-null value.

```javascript
// Normalize: ensure we always have arrays (Retool may wrap Python/query results)
const toArray = (x) => Array.isArray(x) ? x : (x && x.data && Array.isArray(x.data) ? x.data : (x && x.data ? [x.data] : []));
const supplierList = toArray(craft_ftp && craft_ftp.data);
const priceList = toArray(craft_price && craft_price.data);
const optiplyArray = toArray(get_optiply_data && get_optiply_data.data);

// Normalize SKU for matching (FTP often zero-padded "000450", Optiply may have "450")
const norm = (s) => (s == null || s === '') ? '' : String(s).trim().replace(/^0+/, '') || '0';

// 1. Optiply lookup by normalized SKU (must include cost_price for comparison)
const optiplyLookup = {};
optiplyArray.forEach(item => {
  if (item.sku != null) {
    const k = norm(item.sku);
    optiplyLookup[k] = item;
  }
});

// 2. Stock lookup from FTP: key by normalized SKU (support both 'SKU'/'Stock' and 'sku'/'stock')
const stockBySku = {};
supplierList.forEach(item => {
  const sku = norm(item['SKU'] ?? item['sku'] ?? '');
  const stock = item['Stock'] ?? item['stock'];
  if (sku) stockBySku[sku] = stock;
});

// 3. Price lookup from FTP: key by normalized SKU
const priceBySku = {};
priceList.forEach(p => {
  const sku = norm(p && (p.SKU ?? p.sku ?? ''));
  const price = p && (p.UnitPrice ?? p.unit_price);
  if (sku) priceBySku[sku] = price;
});

// 4. All SKUs that appear in either feed (normalized)
const allSkus = new Set([
  ...Object.keys(stockBySku),
  ...Object.keys(priceBySku)
]);

// 5. Build updates: one row per product that needs a stock and/or price update
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

**Troubleshooting “no stock info”:**

- **Data shape:** Retool can expose Python/query results as a direct array or under `.data`. The script now normalizes with `toArray(...)` so `supplierList` is always an array.
- **SKU mismatch:** FTP often uses zero-padded codes (`000450`) and Optiply may use `450`. The script now normalizes SKUs by trimming and stripping leading zeros so both sides match. If your Optiply SKUs use a different convention (e.g. always 6 digits with leading zeros), you may need to adjust the `norm` function.
- **Quick check:** Temporarily return `{ supplierCount: supplierList.length, stockBySkuCount: Object.keys(stockBySku).length, optiplyCount: optiplyArray.length }` to confirm stock data is present and keys are built.

**Inputs:**

- `craft_ftp.data` → stock from block 2 (can be `[]` if only updating price).
- `craft_price.data` → prices from block 3 (can be `[]` if only updating stock).
- `get_optiply_data.data` → array of `{ id, sku, free_stock, cost_price }`.

**Output shape:** `[{ id, free_stock, cost_price }, ...]`

- **Stock and cost price** are both updated in the DB with the single SQL in section 5b (no API needed).

---

## 5. Get Optiply data (for mapping)

Query must return **id**, **sku**, **free_stock**, and **cost_price** (column name in DB is `cost_price`) so the mapping can compare and decide stock/price updates.

- **SQL** (if you use Optiply DB):

```sql
SELECT
  sp.id,
  sp.sku,
  sp.free_stock,
  sp.cost_price
FROM supplier_products sp
WHERE sp.supplier_id = 768200
  AND sp.deleted_at IS NULL
  AND sp.status = 'enabled';
```

- **REST**: Use the Optiply API endpoint that returns supplier products including `cost_price` (or the JSON:API equivalent).

---

## 5b. Update free_stock and cost_price in DB (SQL)

After **map_suppliers**, update both `free_stock` and `cost_price` (and `updated_at`) in one query. Each column is only set when the update row has a non-null value, so stock-only and price-only updates stay independent.

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

Flow: **craft_ftp** + **craft_price** + **get_optiply_data** (all in parallel) → **map_suppliers** → this SQL (no API needed for stock).

---

## 6. Product price on FTP

Yes. There is a **Price** folder with **PRICE.XML** on the same FTP.

| Field | Description |
|-------|-------------|
| **ProductCodeSupplier** | Same product id as stock (e.g. `000450`) |
| **UnitPrice** | Unit price (e.g. `24.06`) |
| **SuggestedRetailPriceEx** | Suggested retail excl. VAT |
| **SuggestedRetailPriceIn** | Suggested retail incl. VAT |
| **PriceUnit** | Unit (e.g. `Stuk`, `Set`) |
| **Stagger** (optional) | Quantity breaks: `FromQuantity`, `FromPrice` |

Path: `Price/PRICE.XML`. Root element: `<Quantore_Price>`, then `<Price>` elements. You can add a second Python block that `cwd('Price')`, `RETR PRICE.XML`, and parses `<Price>` to get `ProductCodeSupplier` + `UnitPrice` (and optionally suggested retail) for syncing prices to Optiply.

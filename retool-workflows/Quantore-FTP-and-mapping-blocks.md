# Quantore: FTP data block + mapping with Optiply

## 1. Product identifier match check

| Source | Field | Format | Example |
|--------|--------|--------|--------|
| **FTP** (StockV4/STOCK.XML) | `ProductCodeSupplier` | 6-digit, often zero-padded | `000450`, `009001`, `110003` |
| **Optiply** (export / supplier_products) | `sku` | 5–7 digit, some leading zeros | `091232`, `110003`, `800252`, `1385455` |

**Conclusion:** The same identifier is used on both sides (supplier product code). Matching is done by **trimmed string**:

- FTP → `SKU` (from `ProductCodeSupplier`)
- Optiply → `sku` (from `supplier_products`)

**From your export (`quantore-supplier-product-sku.json`):**

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

## 3. Block: Map FTP stock to Optiply (JavaScript – `map_suppliers`)

Use this in a **JavaScript** query that runs after:

1. The FTP block above (e.g. `craft_ftp`).
2. A query that returns Optiply supplier products with `id`, `sku`, `free_stock` (same shape as your export or `get_optiply_data`).

It builds a lookup by **trimmed SKU** (so Optiply SKUs with spaces still match) and returns only rows where stock changed, for use in the update loop.

```javascript
// 1. Get Data
const supplierList = craft_ftp.data || [];
const optiplyList = get_optiply_data.data || [];
const optiplyArray = Array.isArray(optiplyList) ? optiplyList : (optiplyList.data || []);

// 2. Build Lookup Map (Key = trimmed SKU, so "800313 " matches "800313")
const optiplyLookup = {};
optiplyArray.forEach(item => {
  if (item.sku != null) {
    const key = String(item.sku).trim();
    optiplyLookup[key] = item;
  }
});

// 3. Compare and Return Only Updates
const discrepancies = supplierList.reduce((acc, ftpItem) => {
  const ftpSku = String(ftpItem['SKU'] || '').trim();
  const stockRaw = ftpItem['Stock'];

  if (!ftpSku) return acc;
  if (stockRaw === null || stockRaw === undefined || String(stockRaw).trim() === '') return acc;

  const newStock = parseInt(stockRaw, 10);
  if (Number.isNaN(newStock)) return acc;

  const dbItem = optiplyLookup[ftpSku];

  if (dbItem) {
    const currentStock = dbItem.free_stock;
    if (currentStock === null || parseInt(currentStock, 10) !== newStock) {
      acc.push({
        sp_id: dbItem.id,
        free_stock: newStock
      });
    }
  }

  return acc;
}, []);

return discrepancies;
```

**Inputs:**

- `craft_ftp.data` → result of the Python block above.
- `get_optiply_data.data` → array of `{ id, sku, free_stock }` (e.g. from SQL or from `quantore-supplier-product-sku.json`-shaped API).

**Output shape:** `[{ sp_id: 29788117, free_stock: 10 }, ...]` for use in the loop that PATCHes Optiply (e.g. `update_sp`).

---

## 4. Get Optiply data (for mapping)

Your export has the right shape. In Retool you typically load the same data with a **SQL** or **REST** query, e.g.:

- **SQL** (if you use Optiply DB):

```sql
SELECT
  sp.id,
  sp.sku,
  sp.free_stock
FROM supplier_products sp
WHERE sp.supplier_id = 768200
  AND sp.deleted_at IS NULL
  AND sp.status = 'enabled';
```

- **REST**: If you use the Optiply API, use the endpoint that returns supplier products with `id`, `sku`, and `free_stock` (or the JSON:API equivalent). The mapping block supports both a plain array and `get_optiply_data.data` (or `.data` from the API response).

Flow: **craft_ftp** → **get_optiply_data** (both run in parallel if you want) → **map_suppliers** → loop over `map_suppliers.data` to PATCH each `sp_id` with `free_stock`.

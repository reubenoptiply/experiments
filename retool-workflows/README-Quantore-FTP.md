# Quantore supplier stock workflow (FTP → Optiply)

## FTP discovery summary

**Host:** `ftp.quantore.com`  
**Stock file location:** `StockV4/STOCK.XML` (not `Data/stock.xml`)

### Root folders on FTP

| Folder     | Content              |
|-----------|----------------------|
| StockV4   | **STOCK.XML** (stock data) |
| Product   | PRODUCT.XML          |
| Price     | (price data)         |
| Delivery  | DELX*.XML delivery files |
| EAN, History, Invoice, OpenOrder, Orderstatus, Upload, ALT | Other data |

### Stock file format (StockV4/STOCK.XML)

- **Product identifier:** `ProductCodeSupplier` (e.g. `000450`, `009001`)
- **Stock quantity:** `AvailableStock` (integer)
- Optional: `WarehouseCode`, `DateNextDelivery`

XML structure:

```xml
<StockMessage>
  <Envelop>...</Envelop>
  <Stock>
    <WarehouseCode>01</WarehouseCode>
    <ProductCodeSupplier>000450</ProductCodeSupplier>
    <AvailableStock>0</AvailableStock>
    <DateNextDelivery>20260323</DateNextDelivery>
  </Stock>
  ...
</StockMessage>
```

## Workflow template

`Update supplier stock (Quantore).json` is configured to:

1. **craft_ftp** (Python): Connect to FTP, `cwd('StockV4')`, download `STOCK.XML`, parse `<Stock>` elements and output `{ "SKU": ProductCodeSupplier, "Stock": AvailableStock }`.
2. **get_optiply_data**: Load Optiply supplier products (e.g. `supplier_id = 768200`).
3. **map_suppliers**: Match FTP SKU to Optiply SKU and build list of `{ sp_id, free_stock }` where stock changed.
4. **update_sp** (loop): PATCH Optiply API to update `freeStock` per supplier product.

Credentials (username/password) are in the **craft_ftp** block; consider moving them to Retool resource or environment variables for production.

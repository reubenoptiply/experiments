# T1: Build the Simulation Python Block (Retool)

## What

Port the simulation engine from `file:demo-account-simulator/python-approach/src/simulation.py` into a self-contained Retool Python block. This is the foundation — all Creator workflow blocks consume its output.

## Scope

**In:**
- Pure Python implementation (no `numpy`, no `pandas`) — replace `np.exp` with `math.exp`, `np.random.normal` with `random.gauss`
- All 12 demand archetypes: Stable Fast/Slow, Seasonal (Summer/Winter/Holiday/Micro), Positive/Negative Trend, Stockout Prone, New Launch (Success/Flop), Outlier, Lumpy, Sporadic, Obsolete, Container, Multi-Supplier, Step Change
- Archetype parsed from product name: text inside `(...)` e.g. `"Lipstick (Seasonal Summer)"` → `"Seasonal Summer"`
- 365-day daily loop per product: inbound deliveries → sales → ROP check → reorder
- Returns a single dict: `{ "stocks": [...] }` — sell_orders and buy_orders are NOT generated (existing DB data is date-shifted)

**Out:**
- No DB writes, no API calls — pure computation only
- No UI

## Data quality fixes (critical)

These are the root cause of the previous data inconsistencies:

| Fix | Detail |
|---|---|
| ROP safety buffer | `reorder_point = lead_time × avg_daily × 1.5` — triggers reorders early enough to prevent unintended stockouts |
| Seasonal pre-ordering | For Seasonal archetypes, ROP is raised to `× 2.5` starting 60 days before the Gaussian peak day |
| Stock floor | `sim_stock = max(0, sim_stock)` at every step — no negative stock ever written to output |
| Sell cap | `sold = min(demand, sim_stock)` — sales never exceed available stock |
| Stockout Prone only | ROP deliberately cut to `0.8 × lead_time × avg_daily` in last 90 days — stockouts only for this archetype |
| New Launch stock injection | Stock injected on launch day (`history_days - 30`), not at simulation start |

## Output structure

Each element in `stocks[]` must include all fields required for the downstream SQL insert:
- `product_id` (int)
- `product_uuid` (uuid string)
- `webshop_id` (int, always 1380)
- `webshop_uuid` (uuid string, from `fetch_products`)
- `on_hand` (int, ≥ 0)
- `date` (string, format `YYYY-MM-DD 00:00:02`)

No sell_orders or buy_orders arrays needed — those tables are date-shifted in-place.

## Acceptance criteria

- Block runs in Retool without import errors (no numpy/pandas)
- All 12 archetypes produce non-negative stock at every day
- Stockouts (stock = 0 for multiple consecutive days) appear only for `Stockout Prone` products
- Seasonal products show a clear demand peak with stock available at peak (no stockout at peak)
- Output dict contains `stocks` array with correct field names (product_id, product_uuid, webshop_id, webshop_uuid, on_hand, date)
- No sell_orders or buy_orders in output

## Spec references
- `spec:ed4445ac-7cc8-4778-912d-6824d7f919b1/8258a28c-e4aa-4648-a4a8-a1a439255d6e` — Tech Plan §1 (constraints), §3 (simulation logic summary)
- `file:demo-account-simulator/python-approach/src/simulation.py` — source to port

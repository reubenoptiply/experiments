-- Sample seed data: Hairaction (Deck) — Retool Database
-- Run after schema_deck_tables.sql
--
-- Credentials are NOT stored in these tables:
--   • Deck API: set x-deck-client-id / x-deck-secret on HTTP blocks (or Retool env vars).
--   • EnsureConnection: username = reuben@optiply.nl — password only in Retool secrets / workflow.
--
-- source_guid matches your Deck portal configuration.

-- ─────────────────────────────────────────────────────────────────────────────
-- 1) deck_supplier_portal_config
-- ─────────────────────────────────────────────────────────────────────────────

INSERT INTO deck_supplier_portal_config (supplier_id, supplier_name, source_guid, is_active)
VALUES (
  'hairaction',
  'Hairaction',
  'cd0c814e-2d94-47b8-ab70-d791730f4ef8',
  true
)
ON CONFLICT (supplier_id) DO UPDATE SET
  supplier_name = EXCLUDED.supplier_name,
  source_guid   = EXCLUDED.source_guid,
  is_active     = EXCLUDED.is_active;

-- Same portal, alias id used by www26_hardcoded_buy_order.js (demoSupplierId):
INSERT INTO deck_supplier_portal_config (supplier_id, supplier_name, source_guid, is_active)
VALUES (
  'hairaction-demo',
  'Hairaction',
  'cd0c814e-2d94-47b8-ab70-d791730f4ef8',
  true
)
ON CONFLICT (supplier_id) DO UPDATE SET
  supplier_name = EXCLUDED.supplier_name,
  source_guid   = EXCLUDED.source_guid,
  is_active     = EXCLUDED.is_active;

-- ─────────────────────────────────────────────────────────────────────────────
-- 2) deck_jobs — sample row (ready to drive EnsureConnection / AddItemsToCart)
--
--    SKUs use the supplier-portal product titles you listed (per your note).
--    Adjust quantities and expected_price before a live run if needed.
-- ─────────────────────────────────────────────────────────────────────────────

-- Use supplier_id that matches fetch_supplier_portal_config in your workflow (hairaction vs hairaction-demo).

INSERT INTO deck_jobs (
  supplier_id,
  customer_id,
  bo_id,
  items,
  status
)
VALUES (
  'hairaction-demo',
  'www26-demo',
  'BO-2026-DEMO-001',
  $items$[
    {
      "sku": "Fanola OroTherapy Gold Fluid Leave-in - 200 ml",
      "quantity": 6,
      "expected_price": "€14.50"
    },
    {
      "sku": "Ga.Ma iQ2 Perfetto Professional Föhn - Rosé Goud",
      "quantity": 2,
      "expected_price": "€89.00"
    },
    {
      "sku": "Fanola No Yellow Zilvershampoo - 100 ml",
      "quantity": 24,
      "expected_price": "€6.20"
    },
    {
      "sku": "Olaplex No. 4C Bond Maintenance Clarifying Shampoo - 250 ml",
      "quantity": 8,
      "expected_price": "€22.90"
    }
  ]$items$::jsonb,
  'pending'
);

-- ─────────────────────────────────────────────────────────────────────────────
-- 3) Optional: completed job with mock results (UI / email preview testing only)
--    Uncomment and run once; or duplicate and change id via RETURNING from (2).
-- ─────────────────────────────────────────────────────────────────────────────
/*
INSERT INTO deck_jobs (
  supplier_id,
  customer_id,
  bo_id,
  items,
  job_guid,
  access_token,
  status,
  results
)
VALUES (
  'hairaction-demo',
  'www26-demo',
  'BO-2026-DEMO-ARCHIVE',
  $items$[
    {"sku": "Fanola OroTherapy Gold Fluid Leave-in - 200 ml", "quantity": 6, "expected_price": "€14.50"},
    {"sku": "Ga.Ma iQ2 Perfetto Professional Föhn - Rosé Goud", "quantity": 2, "expected_price": "€89.00"},
    {"sku": "Fanola No Yellow Zilvershampoo - 100 ml", "quantity": 24, "expected_price": "€6.20"},
    {"sku": "Olaplex No. 4C Bond Maintenance Clarifying Shampoo - 250 ml", "quantity": 8, "expected_price": "€22.90"}
  ]$items$::jsonb,
  'sample-job-guid-archive',
  null,
  'completed',
  $results${
    "items": [
      {
        "sku": "Fanola OroTherapy Gold Fluid Leave-in - 200 ml",
        "status": "In stock",
        "price": "€14.50",
        "price_is": "As expected",
        "added_to_cart": true
      },
      {
        "sku": "Ga.Ma iQ2 Perfetto Professional Föhn - Rosé Goud",
        "status": "In stock",
        "price": "€91.00",
        "price_is": "Higher than expected",
        "added_to_cart": true
      },
      {
        "sku": "Fanola No Yellow Zilvershampoo - 100 ml",
        "status": "In stock",
        "price": "€6.20",
        "price_is": "As expected",
        "added_to_cart": true
      },
      {
        "sku": "Olaplex No. 4C Bond Maintenance Clarifying Shampoo - 250 ml",
        "status": "Out of stock",
        "price": null,
        "price_is": "As expected",
        "added_to_cart": false
      }
    ]
  }$results$::jsonb
);
*/

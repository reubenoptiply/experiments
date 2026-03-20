-- Deck Supplier Portal — Retool DB schema
-- Run this in your Retool Database resource to create the state store for the Deck integration.
-- See README.md for workflow order and usage.
--
-- Rename legacy tables (if present):
--   ALTER TABLE supplier_portal_config RENAME TO deck_supplier_portal_config;
--   ALTER TABLE sku_mappings RENAME TO deck_sku_mappings;
--
-- If you already have deck_jobs with bo_ids (JSONB array), migrate to bo_id (one BO per job):
--   ALTER TABLE deck_jobs ADD COLUMN IF NOT EXISTS bo_id TEXT;
--   UPDATE deck_jobs SET bo_id = jsonb_array_elements_text(bo_ids)->>0 WHERE jsonb_array_length(bo_ids) > 0;
--   ALTER TABLE deck_jobs DROP COLUMN IF EXISTS bo_ids;
--   ALTER TABLE deck_jobs ALTER COLUMN bo_id SET NOT NULL;  -- after backfill

-- Central table: tracks each Deck job through its lifecycle (EnsureConnection → AddItemsToCart → CloseConnection).
-- One job per buy order (BO); the BO can have many line items (BOLs), stored in items.
CREATE TABLE IF NOT EXISTS deck_jobs (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_guid        TEXT,
  supplier_id     TEXT NOT NULL,
  customer_id     TEXT NOT NULL,
  bo_id           TEXT NOT NULL,
  items           JSONB NOT NULL DEFAULT '[]',
  access_token    TEXT,
  status          TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'connecting', 'adding_items', 'completed', 'needs_review', 'failed')),
  results         JSONB,
  error_message   TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_deck_jobs_job_guid ON deck_jobs (job_guid);
CREATE INDEX IF NOT EXISTS idx_deck_jobs_status ON deck_jobs (status);
CREATE INDEX IF NOT EXISTS idx_deck_jobs_supplier_status ON deck_jobs (supplier_id, status);
CREATE INDEX IF NOT EXISTS idx_deck_jobs_updated_at ON deck_jobs (updated_at);

-- Per-supplier Deck configuration (source_guid from Deck; credentials in env vars for pilot).
CREATE TABLE IF NOT EXISTS deck_supplier_portal_config (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  supplier_id     TEXT NOT NULL UNIQUE,
  supplier_name   TEXT NOT NULL,
  source_guid     TEXT NOT NULL,
  is_active       BOOLEAN NOT NULL DEFAULT true,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_deck_supplier_portal_config_supplier_id ON deck_supplier_portal_config (supplier_id);

-- Maps Optiply internal SKU to the SKU the supplier portal expects (per supplier).
CREATE TABLE IF NOT EXISTS deck_sku_mappings (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  supplier_id     TEXT NOT NULL,
  optiply_sku     TEXT NOT NULL,
  supplier_sku    TEXT NOT NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (supplier_id, optiply_sku)
);

CREATE INDEX IF NOT EXISTS idx_deck_sku_mappings_supplier ON deck_sku_mappings (supplier_id);

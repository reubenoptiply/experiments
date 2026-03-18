-- Deck Supplier Portal — Retool DB schema
-- Run this in your Retool Database resource to create the state store for the Deck integration.
-- See README.md for workflow order and usage.

-- Central table: tracks each Deck job through its lifecycle (EnsureConnection → AddItemsToCart → CloseConnection).
CREATE TABLE IF NOT EXISTS deck_jobs (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_guid        TEXT,
  supplier_id     TEXT NOT NULL,
  customer_id     TEXT NOT NULL,
  bo_ids          JSONB NOT NULL DEFAULT '[]',
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
CREATE TABLE IF NOT EXISTS supplier_portal_config (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  supplier_id     TEXT NOT NULL UNIQUE,
  supplier_name   TEXT NOT NULL,
  source_guid     TEXT NOT NULL,
  is_active       BOOLEAN NOT NULL DEFAULT true,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_supplier_portal_config_supplier_id ON supplier_portal_config (supplier_id);

-- Maps Optiply internal SKU to the SKU the supplier portal expects (per supplier).
CREATE TABLE IF NOT EXISTS sku_mappings (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  supplier_id     TEXT NOT NULL,
  optiply_sku     TEXT NOT NULL,
  supplier_sku    TEXT NOT NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (supplier_id, optiply_sku)
);

CREATE INDEX IF NOT EXISTS idx_sku_mappings_supplier ON sku_mappings (supplier_id);

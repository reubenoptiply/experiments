# Demo Account Simulator – Improvement and Implementation Plan

## Current state summary

- **Purpose**: Digital-twin demo for Optiply Shop 1380 (Cosmetics): a Python engine that generates 365 days of synthetic inventory/sales/PO history and a daily "maintainer" that shifts dates forward.
- **Stack**: FastAPI app, PostgreSQL (SQLAlchemy), [simulation.py](../python-approach/src/simulation.py) (demand archetypes + supply loop), [database.py](../python-approach/src/database.py) (wipe, batch insert, maintenance shift), Retool Workflows for orchestration.
- **Spec**: [CONTEXT.md](CONTEXT.md) defines product archetypes, Phase A (Creator) / Phase B (Maintainer), product ID whitelist, and safety constraints.

---

## Suggested implementation order

1. **Bug fixes**: Add `supplier_id` to API and enforce product whitelist; verify/fix batch insert.
2. **Safety and spec**: Centralize whitelist, align date formats and ON CONFLICT with schema.
3. **Robustness**: Error handling and transactional behavior for wipe+insert; health check; fail-fast if no DB.
4. **Docs and API**: Update CONTEXT.md (typo, API contract, dev section); README and .env.example.
5. **Tests**: Unit tests for DemandEngine and SupplyChainSimulator; optional integration test.
6. **Retool**: Document workflow expectations and any batching/throttling for Public API calls.
7. **Gemini handoff**: Add Development/Handoff section and keep context file in sync after changes.

---

## High-level flow

- **Trigger**: Retool Webhook or Cron (nightly).
- **Retool**: Get products (with `supplier_id`) for whitelisted IDs and shop 1380 → POST /simulate → POST api_payloads (sales, buy_orders) to Optiply Public API in batches with delay → POST /maintain (nightly).
- **Engine**: main.py (FastAPI), simulation.py (demand + supply loop), database.py (wipe/insert/maintenance).

When implementing, follow this plan and the spec in [CONTEXT.md](CONTEXT.md). Update the plan or CONTEXT.md if you change scope or API. Whenever you make a change, update CONTEXT.md (especially §8) so we know what's going on.

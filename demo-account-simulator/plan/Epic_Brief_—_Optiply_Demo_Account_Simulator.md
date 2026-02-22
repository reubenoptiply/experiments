# Epic Brief — Optiply Demo Account Simulator

## Summary

Optiply needs a reliable, always-live demo environment for sales account executives to use during prospect demos. The demo runs on Shop 1380 (Cosmetics) and must show 365 days of realistic inventory, sales, and purchase order history — covering the full range of supply chain scenarios Optiply is built to solve. Two Retool Workflows power this: a **Creator** (run manually to reset the account — shifts all existing order dates to end at today and regenerates stock history) and a **Maintainer** (runs nightly to keep data current and undo any changes made during demos). The entire system runs inside Retool — no external services — using direct SQL for all data operations and the Optiply Public API for agenda replanning.

---

## Context & Problem

**Who is affected:** Sales account executives at Optiply who demo the product to prospects.

**Where in the product:** The Optiply dashboard (Shop 1380) — specifically the inventory overview, purchase advice (agenda), buy orders, sell orders, stock history, and KPI metrics (service level, turnover, open POs).

**The current pain:**
- The demo account has been set up manually and ad-hoc, leading to data inconsistencies — stocks and sales don't align, stockouts appear at the wrong times, and the data doesn't look like a real cosmetics business.
- After a demo, account execs may place buy orders, phase out products, or change settings — leaving the account in a broken state for the next demo.
- There is no automated daily reset, so the data goes stale (dates fall behind today) and the dashboard stops looking "live."
- The previous Retool workflow attempts had disconnected blocks, hardcoded date intervals, and destructive operations (deleting instead of shifting), making them unreliable and hard to debug.

**Why it matters:** A compelling, realistic demo is a direct input to sales conversion. Stale or inconsistent data undermines prospect trust in the product before the sales conversation even begins.

---

## Scope

| Area | In scope |
|---|---|
| Creator Workflow | Full reset: calculate dynamic lag, shift existing sell/buy order dates to end at today, soft-delete + regenerate stock history, set up promotions + composed products, replan agenda |
| Maintainer Workflow | Nightly: calculate dynamic lag, shift sell/buy order dates, soft-delete + regenerate stocks, delete manual BOs, restore phased-out products, replan agenda per supplier |
| Simulation quality | Archetypes parsed from product names; realistic ROP logic; stockouts only for designated products |
| Demo features covered | Seasonal demand, trends, stockouts, new launches, promotions, assembly/composed products, purchase agenda |
| Platform | Pure Retool Workflows (Python + JS blocks + SQL + Optiply Public API) |
| Out of scope | Python Cloud Run service, new Optiply product features, multi-shop support |

---

## Success Criteria

- The Creator workflow runs end-to-end without errors and produces a dashboard that looks like a live cosmetics business.
- KPIs show a mixed portfolio: some products healthy, some with visible stockouts, overstock, or slow movement.
- The Maintainer runs nightly and the dashboard always shows today's date as the most recent activity.
- After an account exec demos and makes changes, the next morning the account is fully reset to its clean simulated state.

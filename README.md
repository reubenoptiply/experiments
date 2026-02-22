# Optiply Experiments

**Your second brain for product growth.** This repo is the starting point for features and initiatives that drive extra revenue at Optiply—POCs, plans, and execution context in one place.

---

## What this repo is for

- **Product growth** — Strategic initiatives to generate revenue, reduce churn, and differentiate Optiply (AI-powered supply chain, automation, partnerships).
- **Single source of truth** — Briefs, tech plans, roadmaps, and runbooks so you (and tools like Cursor or Gemini) can pick up any project quickly.
- **Experiments & POCs** — From high-level strategy down to runnable code and Retool workflows.

Everything here supports the same north star: **turn Optiply from an inventory optimization tool into an AI-powered operating system for end-to-end supply chain management.**

---

## Repository map

| Project | What it is | Where to start |
|--------|------------|----------------|
| **[product-growth-plan](./product-growth-plan/)** | Product growth roadmap 2026: strategy, initiatives, and business impact. | [1-min summary](./product-growth-plan/1-min-summary.md) → [5-min](./product-growth-plan/5-min-summary.md) → [roadmap](./product-growth-plan/product-growth-roadmap.md) |
| **[deck-supplier-portals](./deck-supplier-portals/)** | Deck × Optiply: automate PO entry in supplier portals (eliminate double data entry). | [Context & implementation](./deck-supplier-portals/context-and-implementation.md) → [Tech plan (Retool)](./deck-supplier-portals/tech-plan-retool.md) |
| **[demo-account-simulator](./demo-account-simulator/)** | Digital-twin demo for Shop 1380: synthetic inventory/sales/PO history and daily maintainer. | [README](./demo-account-simulator/README.md) → [Retool plan](./demo-account-simulator/plan/README.md) → [Execution runbook](./demo-account-simulator/plan/EXECUTION_RUNBOOK.md) |

---

## Product growth at a glance

The 2026 roadmap centers on **five initiatives** (see [product-growth-plan](./product-growth-plan/)):

1. **AI-powered PO data input** (Deck) — Eliminate double data entry in supplier portals.  
2. **Supplier email analysis** — Auto-apply updates from supplier emails.  
3. **In-house EDI integration** — Replace expensive third-party EDI.  
4. **3-way matching automation** — PO / GRN / invoice verification.  
5. **Container optimization** — Freight partnerships and logistics optimization.

This repo holds the **plans and execution details** for these and related work (e.g. demo environment, Retool workflows).

---

## How to use this repo

- **Catch up on strategy** — Start with [product-growth-plan/1-min-summary.md](./product-growth-plan/1-min-summary.md), then drill into the roadmap or agentic layer as needed.
- **Execute a project** — Open the project folder (e.g. `demo-account-simulator/plan/` or `deck-supplier-portals/`) and follow its README or runbook.
- **Onboard someone (or an AI)** — Point them here; the table above and each project’s README are the entry points.
- **Keep it current** — When you add a new initiative or change scope, update this README and the relevant project’s docs so the “second brain” stays accurate.

---

## Conventions

- **Briefs & specs** — Stored in the project folder (e.g. `plan/`, `docs/`) with a clear name (Epic Brief, Tech Plan, CONTEXT.md).
- **Execution** — Runbooks and builder guides live next to the plan (e.g. `demo-account-simulator/plan/EXECUTION_RUNBOOK.md`).
- **Single source of truth** — Each project has one main context/spec file; other docs link to it and note when they’re stubs or TBD.

---

*Experiments — Optiply Product Growth. Start here.*

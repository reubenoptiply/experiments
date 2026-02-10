# Epic Brief: Product Growth Roadmap 2026

## Summary

This Epic defines Optiply's comprehensive Product Growth Roadmap for 2026, unifying the existing Agentic Layer Platform with four strategic growth initiatives to establish market leadership in AI-powered supply chain automation. Building on the foundation of the **Optiply Strategic Agent Platform** (LangGraph-based infrastructure with six specialized agents), we will deliver end-to-end automation from supplier communication through invoice matching. The roadmap prioritizes AI-powered PO data input via Deck partnership (Q1-Q2), supplier email conversation analysis (Q2), in-house EDI integration (Q2-Q3), and 3-way matching automation (Q3-Q4). These initiatives drive four competitive differentiators: complete end-to-end automation, AI-first platform capabilities, comprehensive ecosystem integration, and 70%+ reduction in manual operational work. Success is measured through business impact metrics—revenue growth (ARR/MRR expansion), customer retention improvement, and NPS gains—with a balanced ROI story combining cost savings, revenue growth, and market positioning. The roadmap serves all customer segments as platform-wide improvements, executed through a mix of internal development and strategic external partnerships.

## Context & Problem

### Who's Affected

**Primary Stakeholders:**

- **Product Growth Leadership**: Driving strategic initiatives that differentiate Optiply in the market and accelerate business growth
- **Executive Management**: Evaluating investment priorities, ROI expectations, and competitive positioning
- **All Customer Segments**: SMB, mid-market, and enterprise customers seeking operational efficiency and automation
- **Engineering Teams**: Building and integrating new capabilities across the platform
- **Operations & Supply Chain Teams**: End users who will benefit from reduced manual work and improved automation
- **Sales & Customer Success**: Teams positioning Optiply's differentiated capabilities to prospects and customers

### Where in the Product

This Epic spans the **entire Optiply platform ecosystem**, touching:

- **Existing Agentic Layer** (from file:product-growth-plan/agentic-optiply.md):
  - Data-quality/Onboarding Agent (early prototyping → MVP)
  - Order Agent (roadmap months 3-5)
  - Strategic/Supply-chain Agent (roadmap months 3-4)
  - Data Co-pilot (MVP in parallel)
  - Explanatory Agent (vendor solution via Intercom Fin)
  - Web-scraping/Browser Agent (external team via Deck)
- **New Growth Initiatives**:
  - AI-powered PO data input in supplier portals (eliminates double data entry)
  - Supplier email conversation analysis and automation
  - In-house EDI integration infrastructure
  - 3-way matching automation (PO/GRN/Invoice verification)
  - Container optimization pilot (freight forwarder partnerships)
- **Existing ERP Integrations**: Optiply → Customer ERP sync (orders placed in Optiply automatically sync to customer systems)
- **Platform Foundation**: LangGraph-based Strategic Agent Platform (src/)

### Current Pain Points

**1. Fragmented Growth Strategy**

Multiple initiatives are progressing without a unified strategic narrative that demonstrates how they collectively drive business growth. Management lacks visibility into how individual capabilities combine to create competitive differentiation and measurable business impact. The existing Agentic Layer Roadmap focuses on technical execution but doesn't articulate the growth story needed for strategic decision-making.

**2. Incomplete Automation Coverage**

While Optiply provides intelligent inventory optimization and PO advice with ERP integration, critical gaps remain in the end-to-end workflow:

- **Double data entry**: Customers place orders in Optiply (syncs to ERP ✓), but must manually re-enter data in supplier portals (✗)
- **Supplier communication** is manual (emails require manual reading and system updates)
- **EDI integration** relies on expensive third-party processors
- **Invoice verification** (3-way matching) is time-consuming and error-prone with unstructured PDFs
- **Logistics optimization** is not integrated with inventory optimization (missed cost savings)
- These gaps prevent Optiply from delivering the "70%+ manual work reduction" promise

**3. Competitive Pressure**

The supply chain SaaS market is rapidly adopting AI capabilities. Without a clear roadmap demonstrating AI-first, end-to-end automation, Optiply risks:

- Losing differentiation against competitors
- Missing opportunities with larger enterprise customers who demand comprehensive automation
- Slower revenue growth and higher churn as customers seek more complete solutions

**4. Unclear Business Value Narrative**

Existing initiatives lack clear articulation of business impact:

- How do these capabilities drive revenue growth (ARR/MRR expansion)?
- What is the retention/churn impact?
- How do we measure customer satisfaction (NPS) improvements?
- What is the balanced ROI story (cost savings + revenue + market position)?

**5. Dependency and Resource Coordination**

With a mix of internal development and external partnerships (Deck, Intercom Fin, EDI standards bodies), teams need clarity on:

- Critical path dependencies (what blocks what?)
- Resource allocation across parallel tracks
- Partnership coordination and integration timelines
- Technical infrastructure prerequisites (OCR, NLP, integration platform)

### The Core Problem

**We need a unified Product Growth Roadmap that:**

1. **Tells a compelling growth story** to management, demonstrating how 10 integrated capabilities (6 existing agents + 4 new initiatives) drive measurable business impact
2. **Establishes clear competitive differentiation** through end-to-end automation, AI-first platform, ecosystem integration, and operational efficiency
3. **Sequences initiatives strategically** based on priority (Deck PO input → Email analysis → EDI → 3-way matching) while managing dependencies
4. **Defines success through business metrics** (revenue, retention, NPS) rather than just feature delivery
5. **Balances the ROI narrative** across cost savings, revenue growth, and market positioning
6. **Coordinates resources effectively** across internal teams and external partnerships
7. **Serves all customer segments** with platform-wide improvements that scale from SMB to enterprise

Without this unified roadmap, Optiply risks building capabilities in isolation, missing the strategic narrative that drives investment decisions, competitive differentiation, and ultimately, business growth.

### Success Criteria

**Business Impact Metrics:**

- **Revenue Growth**: Measurable ARR/MRR expansion driven by new capabilities
- **Customer Retention**: Reduced churn through increased platform value and automation
- **NPS Improvement**: Higher customer satisfaction from operational efficiency gains

**Competitive Positioning:**

- Market recognition as AI-first supply chain platform
- Win rate improvement against competitors in enterprise deals
- Thought leadership in end-to-end supply chain automation

**Operational Efficiency:**

- 70%+ reduction in manual work across supplier communication, data entry, and invoice processing
- Platform scalability supporting larger enterprise customers
- Successful integration of all capabilities into cohesive workflows
- Container optimization pilot validated with 5-10 customers, demonstrating cost savings and supply chain efficiency gains

&nbsp;
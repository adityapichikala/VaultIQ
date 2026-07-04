# Q2 2026 Product Roadmap

**Owner:** Product Management  
**Status:** Approved by CPO on April 1, 2026  
**ACL:** engineering, leadership

---

## Strategic Priorities

1. **Payments Reliability** — Reduce failed transactions from 2.1% to <0.5%
2. **AI-First Search** — Replace keyword search with semantic + LLM-powered search
3. **Enterprise Tier** — Launch the enterprise product by August 2026
4. **Mobile Performance** — App cold start < 2 seconds on mid-range Android devices

## Roadmap by Team

### Payments Team (Amit Joshi)

| Feature | Priority | Target Date | Status |
|---------|----------|------------|--------|
| UPI 2.0 integration | P0 | Apr 30 | ✅ Shipped |
| Payment retry with exponential backoff | P0 | May 15 | ✅ Shipped |
| Razorpay → Juspay migration (50% traffic) | P1 | Jun 30 | 🔄 In Progress |
| International payments (Stripe) | P1 | Jul 31 | 📋 Planned |
| Subscription billing engine | P2 | Aug 31 | 📋 Planned |

### Marketplace Team (Ravi Shankar)

| Feature | Priority | Target Date | Status |
|---------|----------|------------|--------|
| Semantic search v1 (embeddings) | P0 | May 31 | ✅ Shipped |
| Personalized recommendations | P1 | Jun 30 | 🔄 In Progress |
| Seller analytics dashboard | P1 | Jul 15 | 🔄 In Progress |
| Dynamic pricing engine | P2 | Aug 15 | 📋 Planned |
| Multi-language listings (Hindi, Tamil) | P2 | Sep 15 | 📋 Planned |

### GenAI Team (Karthik Venkat)

| Feature | Priority | Target Date | Status |
|---------|----------|------------|--------|
| Internal knowledge base RAG (VaultIQ) | P0 | Jul 31 | 🔄 In Progress |
| Customer support copilot v1 | P1 | Aug 31 | 📋 Planned |
| Auto-generate product descriptions | P2 | Sep 15 | 📋 Planned |

### Mobile Team (Priyanka Das)

| Feature | Priority | Target Date | Status |
|---------|----------|------------|--------|
| Cold start optimization | P0 | May 31 | ✅ Shipped (1.8s achieved) |
| Offline mode for catalog browsing | P1 | Jul 15 | 🔄 In Progress |
| Push notification revamp | P2 | Aug 15 | 📋 Planned |

## Dependencies & Risks

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Juspay migration delay | Payments reliability target at risk | Run parallel for 2 months, gradual traffic shift |
| GenAI costs exceeding budget | ₹15L/month LLM costs if not optimized | Implement caching + model cascading (small → large) |
| Hiring delays for enterprise team | Aug launch at risk | Staff from existing teams temporarily |
| Apple App Store review delays | Mobile features delayed | Submit 2 weeks before target |

## OKRs — Q2 2026

**Objective 1: Make payments bulletproof**
- KR1: Failed transaction rate < 0.5% (currently 2.1%)
- KR2: Payment settlement T+0 for 80% of transactions
- KR3: Zero P0 incidents in payments for 60 consecutive days

**Objective 2: Launch AI-powered search**
- KR1: Semantic search live for 100% of users
- KR2: Search click-through rate improves by 15%
- KR3: Customer support tickets about "can't find" reduced by 30%

---

*Next roadmap review: July 1, 2026 (start of Q3 planning).*

# ADR-006: Temporal Recency Decay, Lineage Tracking, and Dataset Management

**Status:** Approved  
**Author:** Pichikala Aditya  
**Date:** 2026-07-21  
**Extends:** ADR-003 (Hybrid Retrieval & RRF), ADR-005 (Decoupled Microservice Architecture)

---

## 1. Context & Problem Statement

In enterprise RAG systems, policy documents, vendor guidelines, and technical SOPs are constantly revised. Over time, repositories contain multiple versions of similar documents (e.g., `leave_policy_2024.md` vs. `leave_policy_2026.md`). 

Without explicit temporal recency mechanisms:
1. **Stale Information Retrieval:** Standard vector similarity (cosine) and BM25 text match may rank an older, highly-keyword-matched 2024 policy document *above* a revised 2026 policy document.
2. **Lack of Comparative Intelligence:** When users explicitly ask *"What changed in the leave policy?"*, standard single-document RAG fails to retrieve and contrast multiple temporal versions side-by-side.
3. **Dataset Lifecycle Friction:** Administrators lack a clean UI surface to delete obsolete datasets or re-index updated dataset versions with timestamp metadata.

---

## 2. Decision

We implement a **three-part Temporal & Dataset Management Architecture**:

### 2.1 Exponential Temporal Decay Scoring ($\lambda$-Decay)

During Reciprocal Rank Fusion (RRF), each chunk's base RRF score is multiplied by an exponential decay factor $\text{Multiplier}(\Delta t)$ based on document age:

$$\Delta t_{\text{days}} = \max\left(0, \text{Today} - \text{EffectiveDate}\right)$$

$$\lambda = \frac{\ln(2)}{\tau_{\text{half\_life}}}$$

$$S_{\text{final}}(\text{chunk}) = S_{\text{RRF}}(\text{chunk}) \times \exp\left(-\lambda \times \Delta t_{\text{days}}\right)$$

Where $\tau_{\text{half\_life}}$ defaults to **180 days** (configurable via API and UI slider). A document 180 days old receives a 50% score penalty relative to a brand-new document, ensuring updated policies naturally override outdated ones.

### 2.2 Dataset Lineage Metadata Schema

All ingested `Document` and `Chunk` objects carry explicit lineage attributes stored in Qdrant payloads and BM25 metadata:

```json
{
  "chunk_id": "doc_hr_01_chunk_0",
  "dataset_name": "hr_policies_v2",
  "version": "2.0",
  "effective_date": "2026-07-21",
  "acl_roles": ["hr", "all-employees"]
}
```

### 2.3 Comparative & Diff Intelligence RAG Prompting

The `RAGChain` system prompt is augmented with **Diff Analysis Instructions**:
When queries contain comparative terms (*"what changed"*, *"difference between"*, *"version comparison"*), the LLM is instructed to format a side-by-side **Key Differences / What Changed** breakdown table.

### 2.4 Reflex Data Studio UI Tab

A dedicated **Data Studio** tab is integrated into the Reflex frontend app, providing:
- Toggle controls for **Recency Decay Weighting**.
- Slider control for **Decay Half-Life (1–3650 days)**.
- Re-index / Rebuild Index trigger communicating with `POST /api/v1/ingest`.
- Dataset deletion endpoint `DELETE /api/v1/datasets/{name}` to purge obsolete index entries.

---

## 3. Consequences

### Positive
- **Automatic Policy Overrides:** Newer policies naturally rank above older ones without deleting historical context.
- **Diff Intelligence:** Users can directly ask for version comparisons and receive structured changelogs.
- **Production-Grade Data Governance:** Full API and UI control over dataset lifecycles.

### Trade-offs / Mitigations
- **Historical Query Bias:** When users explicitly seek historical records (e.g., *"What was the 2022 travel allowance?"*), decay weighting can be toggled OFF via the UI or API request (`apply_temporal_decay=False`).

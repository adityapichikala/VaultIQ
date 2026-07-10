# Thinking Artifact: How I'd Build VaultIQ for Real

**By Pichikala Aditya**  
**Role: LLM Engineer / GenAI Engineer**

## Context & The Pretend Scenario
For the past three weeks, I’ve been building **VaultIQ**, a Retrieval-Augmented Generation (RAG) system designed to tame the unstructured, multi-modal mess of enterprise data (PDFs, Markdown, Slack exports, and CSVs). I built a functional, end-to-end "skinny" version of this product, complete with a hybrid retrieval pipeline and role-based access control (ACL).

However, if a company handed me a team of 3 engineers and 6 months to take VaultIQ from a local prototype to a highly available, enterprise-grade production system, the architecture and roadmap would need to evolve significantly. This memo outlines exactly how I would architect, scale, and secure VaultIQ for the real world.

---

## 1. Production Architecture Evolution

The current prototype relies on a local Streamlit app, a local Qdrant instance, and a local BM25 index built at runtime. In production, we need horizontal scalability, high availability, and asynchronous processing.

### The Ingestion Pipeline (Moving to Async & Streaming)
Instead of a synchronous python script that parses a directory, the real-world ingestion engine would be event-driven. 
- **Message Broker:** When a new file is uploaded to an S3 bucket or a new message drops in Slack, an event would be fired to an **Apache Kafka** or **AWS SQS** queue.
- **Worker Nodes:** A fleet of **Celery** or **Temporal** workers would consume these events, parse the files, chunk them, and generate embeddings. This prevents a large 10,000-page PDF from blocking the system.
- **Model Hosting:** Instead of downloading `all-MiniLM-L6-v2` locally into the worker's memory, we would deploy the embedding model as an independent microservice using **vLLM** or **NVIDIA Triton Inference Server** behind a load balancer, allowing the embedding generation to scale independently from the parsing logic.

### The Vector Database (Moving to Managed Infrastructure)
Local Qdrant is great for prototyping, but enterprise data volumes require distributed storage.
- I would migrate to **Qdrant Cloud** or **Pinecone** (serverless). 
- To handle updates and deletions (e.g., when a document is deleted, its chunks must be purged), the metadata must be strictly indexed. The current SQLite-based BM25 would be replaced by **Elasticsearch** or **OpenSearch**, natively handling the sparse retrieval (BM25) and integrating beautifully with dense vectors via managed Hybrid Search.

### The Generation Layer (Moving to Enterprise APIs)
- Instead of using the free Groq API tier, I would use **Azure OpenAI (GPT-4o)** or **AWS Bedrock (Claude 3.5 Sonnet)** to ensure enterprise data privacy, SLA guarantees, and compliance (SOC2/HIPAA). 
- We would also introduce a **semantic cache** (using Redis + vector search) to cache common queries (e.g., "What is the holiday schedule?"), drastically reducing API costs and latency.

---

## 2. Security and Access Control (ACL)

In the prototype, ACL is handled by simple set intersection (`doc_roles & user_roles`). In a real enterprise with 10,000 employees, this breaks down.

- **Dynamic Entitlements:** I would integrate with the company's Identity Provider (IdP) like **Okta** or **Active Directory**. The system would fetch the user's groups dynamically via OAuth/OIDC tokens at query time.
- **Document-Level Security (DLS):** Both OpenSearch and Qdrant support metadata filtering at the database level. Instead of fetching all results and filtering them in memory (which ruins the Top-K recall), the database itself will enforce the ACL condition during the vector search, guaranteeing mathematically that a user never even computes the similarity of a document they cannot access.

---

## 3. The Roadmap: What the Team Builds in 6 Months

With a team of 3 engineers (1 Data Engineer, 1 Backend/ML Engineer, 1 Frontend Engineer), here is the 6-month execution plan:

### Months 1-2: Data Platform & Ingestion Robustness
- Build the Kafka/Celery async ingestion pipeline.
- Write robust parsers for messy OCR (using AWS Textract or Unstructured.io) to handle scanned PDFs.
- Setup OpenSearch for distributed hybrid retrieval.

### Months 3-4: Evaluation & Guardrails
- **You cannot improve what you cannot measure.** We would establish a golden dataset of 500 ground-truth Q&A pairs.
- Implement **RAGAS** or **TruLens** into the CI/CD pipeline to evaluate context precision, recall, and answer faithfulness on every PR.
- Introduce **NeMo Guardrails** or **Llama Guard** to prevent the LLM from leaking PII, answering out-of-domain questions, or succumbing to prompt injection attacks.

### Months 5-6: User Experience & Observability
- Replace Streamlit with a scalable **Next.js** frontend and a **FastAPI** backend.
- Implement **Langfuse** or **Arize Phoenix** for observability. This allows product managers to track which queries are returning bad results, monitor token usage/costs, and capture user feedback (thumbs up/down).

---

## 4. The Biggest Risks & How I'd Mitigate Them

1. **Stale Data (The "Old Policy" Problem):** An LLM hallucinating based on a 2022 remote work policy is a liability.
   - *Mitigation:* Implement TTL (Time To Live) on embeddings and a rigid versioning system. When a document is updated, the old chunks must be immediately tombstoned in the vector DB.
2. **The "Needle in a Haystack" Retrieval Failure:** Hybrid search helps, but complex multi-hop reasoning (e.g., "Compare the Q1 budget to the Q3 budget") often fails standard RAG.
   - *Mitigation:* Implement an agentic router. If the query requires aggregation, an LLM agent routes the query to a SQL database (Text-to-SQL) instead of relying purely on vector search.

## Conclusion
Building VaultIQ locally proved that the core RAG architecture—hybrid fusion, chunking with metadata persistence, and grounded generation—works. Taking it to production isn't about changing the math; it’s about distributed systems, bulletproof data engineering, and rigorous observability. 

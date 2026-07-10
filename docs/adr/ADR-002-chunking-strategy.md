# ADR-002: Document Chunking Strategy

## Context
When ingesting large enterprise documents (like a 40-page employee handbook or a 100-comment Slack thread), we cannot pass the entire text to an embedding model. Embedding models (like `all-MiniLM-L6-v2`) have a maximum sequence length (typically 256-512 tokens). We need a strategy to split documents into smaller chunks while preserving semantic meaning.

## Decision
We chose a **recursive character-based splitting strategy** combined with structural metadata preservation.

1. **Hierarchy of Separators:** 
   - Paragraphs (`\n\n`)
   - Lines (`\n`)
   - Sentences (`. `)
   - Words (` `)
2. **Parameters:**
   - Target chunk size: 500 characters
   - Overlap: 50 characters (to maintain context across boundaries)
   - Minimum size: 50 characters
3. **Metadata Persistence:**
   - Instead of losing the context of a chunk, each chunk carries the `title`, `source_type`, `source_file`, and `acl_roles` of its parent document.

## Consequences
- **Positive:** Ensures no chunk exceeds the embedding model limit. The overlap helps prevent "cutting a thought in half".
- **Positive:** By preserving structural metadata (like Markdown headers), we retain the context even when text is deeply fragmented.
- **Negative:** Blindly splitting on paragraphs/sentences doesn't always guarantee semantic coherence within a chunk. Sometimes a concept spans multiple chunks, diluting the embedding vector.

## Alternatives considered
- **LangChain `RecursiveCharacterTextSplitter`:** While we effectively implemented this logic, writing it from scratch removes the heavy LangChain dependency, keeping the project "skinny" and defensible.
- **Semantic Chunking:** Using an LLM or cross-encoder to dynamically determine split points. Rejected due to high latency and compute cost during ingestion.

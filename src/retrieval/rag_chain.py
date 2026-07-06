"""
RAG chain module for VaultIQ.
Takes retrieved chunks and generates an answer using Groq (Llama-3-8B)
with inline citations.
"""

import os
from loguru import logger

try:
    from groq import Groq
except ImportError:
    Groq = None

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


SYSTEM_PROMPT = """You are VaultIQ, an enterprise knowledge assistant at BigCorp.
You answer questions based ONLY on the provided context documents.

RULES:
1. Only use information from the provided context. If the context doesn't contain the answer, say "I don't have enough information to answer this based on the available documents."
2. Cite your sources inline using this format: [📄 source_file · section_or_detail]
3. Be concise and professional.
4. If the context contains tables, present data in a structured format.
5. If multiple sources agree, cite the most specific one.
6. Never make up information not in the context.

Example citation: "Employees are eligible for 18 days of earned leave per year [📄 leave_policy.md · Leave Types]"
"""

QUERY_TEMPLATE = """Context documents:
{context}

---

Question: {question}

Answer the question using ONLY the context above. Cite sources inline using [📄 source_file · detail]."""


class RAGChain:
    """Generates answers from retrieved context using Groq LLM."""

    def __init__(
        self,
        model: str = "llama-3.1-8b-instant",
        api_key: str | None = None,
    ):
        """
        Args:
            model: Groq model name.
            api_key: Groq API key. If None, reads from GROQ_API_KEY env var.
        """
        if Groq is None:
            raise ImportError("groq required. Install: pip install groq")

        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError(
                "GROQ_API_KEY not found. Set it as an environment variable or pass it directly."
            )

        self.client = Groq(api_key=self.api_key)
        self.model = model
        logger.info(f"RAG chain initialized with model: {model}")

    def generate(
        self,
        query: str,
        retrieved_chunks: list[dict],
        temperature: float = 0.1,
        max_tokens: int = 1024,
    ) -> dict:
        """Generate an answer from retrieved chunks.

        Args:
            query: User's question.
            retrieved_chunks: List of retrieved chunk dicts.
            temperature: LLM temperature (low = more factual).
            max_tokens: Maximum tokens in the response.

        Returns:
            Dict with 'answer', 'sources', 'model', 'usage'.
        """
        if not retrieved_chunks:
            return {
                "answer": "I couldn't find any relevant documents to answer your question. Please try rephrasing or check if you have access to the relevant documents.",
                "sources": [],
                "model": self.model,
                "usage": {},
            }

        # Format context from chunks
        context = self._format_context(retrieved_chunks)

        # Build the prompt
        user_message = QUERY_TEMPLATE.format(context=context, question=query)

        # Call Groq API
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )

            answer = response.choices[0].message.content
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

            # Extract unique sources
            sources = self._extract_sources(retrieved_chunks)

            logger.info(
                f"Generated answer ({usage['total_tokens']} tokens, model={self.model})"
            )

            return {
                "answer": answer,
                "sources": sources,
                "model": self.model,
                "usage": usage,
            }

        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return {
                "answer": f"Sorry, I encountered an error generating the answer: {str(e)}",
                "sources": [],
                "model": self.model,
                "usage": {},
            }

    def _format_context(self, chunks: list[dict]) -> str:
        """Format retrieved chunks into context string for the prompt."""
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            source = chunk.get("source_file", "unknown")
            title = chunk.get("title", "Untitled")
            source_type = chunk.get("source_type", "unknown")
            content = chunk.get("content", "")

            context_parts.append(
                f"[Source {i}] {source} ({source_type}) — {title}\n{content}"
            )

        return "\n\n---\n\n".join(context_parts)

    @staticmethod
    def _extract_sources(chunks: list[dict]) -> list[dict]:
        """Extract unique source information from chunks."""
        seen = set()
        sources = []
        for chunk in chunks:
            source_file = chunk.get("source_file", "unknown")
            if source_file not in seen:
                seen.add(source_file)
                sources.append({
                    "file": source_file,
                    "title": chunk.get("title", "Untitled"),
                    "type": chunk.get("source_type", "unknown"),
                })
        return sources

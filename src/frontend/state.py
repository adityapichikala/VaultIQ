"""
VaultIQ — Reflex Frontend
A modern, dark-themed enterprise RAG chat interface.
"""

import reflex as rx
import httpx
import json
from typing import AsyncGenerator

API_BASE = "http://localhost:8000/api/v1"

ROLES = ["engineering", "hr", "leadership", "all-employees"]

ROLE_COLORS = {
    "engineering": "#3b82f6",
    "hr": "#ec4899",
    "leadership": "#f59e0b",
    "all-employees": "#10b981",
}

ROLE_ICONS = {
    "engineering": "🛠️",
    "hr": "👥",
    "leadership": "🎯",
    "all-employees": "🌐",
}

SAMPLE_QUESTIONS = [
    "What is our remote work policy?",
    "How do we handle P0 incidents?",
    "What is the leave policy?",
    "Who leads the engineering team?",
]


class Source(rx.Base):
    file: str
    title: str
    type: str


class Message(rx.Base):
    role: str  # "user" or "assistant"
    content: str
    sources: list[Source] = []
    is_streaming: bool = False


class State(rx.State):
    messages: list[Message] = []
    current_role: str = "engineering"
    query: str = ""
    is_loading: bool = False
    qdrant_vectors: int = 0
    bm25_docs: int = 0
    llm_available: bool = False
    health_loaded: bool = False
    error_message: str = ""

    @rx.event
    async def load_health(self):
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"{API_BASE}/health")
                if r.status_code == 200:
                    data = r.json()
                    self.qdrant_vectors = data.get("qdrant_vectors", 0)
                    self.bm25_docs = data.get("bm25_documents", 0)
                    self.llm_available = data.get("llm_available", False)
                    self.health_loaded = True
        except Exception as e:
            self.error_message = f"Backend offline: {str(e)[:60]}"

    @rx.event
    def set_role(self, role: str):
        self.current_role = role

    @rx.event
    def set_query(self, value: str):
        self.query = value

    @rx.event
    def use_sample(self, question: str):
        self.query = question

    @rx.event
    def clear_chat(self):
        self.messages = []
        self.error_message = ""

    @rx.event
    async def send_query(self):
        if not self.query.strip() or self.is_loading:
            return

        user_query = self.query.strip()
        self.query = ""
        self.is_loading = True
        self.error_message = ""

        # Add user message
        self.messages.append(
            Message(role="user", content=user_query)
        )

        # Add placeholder assistant message (streaming)
        self.messages.append(
            Message(role="assistant", content="", is_streaming=True)
        )

        yield

        # Call FastAPI streaming endpoint
        payload = {
            "query": user_query,
            "user_roles": [self.current_role, "all-employees"],
            "top_k": 5,
            "temperature": 0.1,
        }

        full_answer = ""
        sources = []

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                async with client.stream(
                    "POST",
                    f"{API_BASE}/query/stream",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                ) as response:
                    if response.status_code != 200:
                        raise Exception(f"API error {response.status_code}")

                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            try:
                                data = json.loads(data_str)
                                if data.get("done") is False:
                                    token = data.get("token", "")
                                    full_answer += token
                                    # Update the streaming message
                                    self.messages[-1] = Message(
                                        role="assistant",
                                        content=full_answer,
                                        is_streaming=True,
                                    )
                                    yield
                                elif data.get("done") is True:
                                    raw_sources = data.get("sources", [])
                                    sources = [
                                        Source(
                                            file=s.get("file", ""),
                                            title=s.get("title", ""),
                                            type=s.get("type", ""),
                                        )
                                        for s in raw_sources
                                    ]
                            except json.JSONDecodeError:
                                pass

        except Exception as e:
            full_answer = f"⚠️ Error: {str(e)}"
            self.error_message = str(e)

        # Finalize the assistant message
        self.messages[-1] = Message(
            role="assistant",
            content=full_answer,
            sources=sources,
            is_streaming=False,
        )
        self.is_loading = False
        yield

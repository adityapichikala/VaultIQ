"""
VaultIQ — Reflex Frontend
Enterprise RAG Chat + Data Studio (Dataset Management & Temporal Recency Weighting)
"""

from dataclasses import dataclass, field
import reflex as rx
import httpx
import json

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
    "What changed between the old and new leave policy?",
    "Who leads the engineering team?",
]

BG = "#0a0a0f"
BG2 = "#111118"
CARD = "#16161f"
HOVER = "#1e1e2a"
BORDER = "#2a2a3a"
BORDER_A = "#7c3aed"
TXT = "#f0f0f8"
TXT2 = "#8888aa"
MUTED = "#55556a"
PURPLE = "#7c3aed"
BLUE = "#3b82f6"
GREEN = "#10b981"


# ─── Dataclasses ──────────────────────────────────────────────────

@dataclass
class Source:
    file: str = ""
    title: str = ""
    type: str = ""


@dataclass
class Message:
    role: str = ""
    content: str = ""
    sources: list[Source] = field(default_factory=list)
    is_streaming: bool = False


# ─── State ───────────────────────────────────────────────────────

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

    # Navigation & Temporal Decay settings
    active_tab: str = "chat"
    apply_temporal_decay: bool = True
    decay_half_life_days: float = 180.0
    status_message: str = ""

    @rx.event
    def set_tab(self, tab: str):
        self.active_tab = tab

    @rx.event
    def toggle_decay(self, val: bool):
        self.apply_temporal_decay = val

    @rx.event
    def set_half_life(self, val: float):
        self.decay_half_life_days = val

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
        self.active_tab = "chat"

    @rx.event
    def clear_chat(self):
        self.messages = []
        self.error_message = ""

    @rx.event
    async def rebuild_index_now(self):
        self.is_loading = True
        self.status_message = "Rebuilding index with recency weighting..."
        yield
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                r = await client.post(
                    f"{API_BASE}/ingest",
                    json={"force_rebuild": True, "dataset_name": "synthetic_v2", "version": "2.0"},
                )
                if r.status_code == 200:
                    self.status_message = "✅ Index successfully rebuilt!"
                    await self.load_health()
                else:
                    self.status_message = f"⚠️ Ingestion error: {r.status_code}"
        except Exception as e:
            self.status_message = f"⚠️ Error: {str(e)[:60]}"
        self.is_loading = False
        yield

    @rx.event
    async def send_query(self):
        if not self.query.strip() or self.is_loading:
            return

        user_query = self.query.strip()
        self.query = ""
        self.is_loading = True
        self.error_message = ""
        self.active_tab = "chat"

        self.messages = self.messages + [
            Message(role="user", content=user_query),
            Message(role="assistant", content="", is_streaming=True),
        ]
        yield

        payload = {
            "query": user_query,
            "user_roles": [self.current_role, "all-employees"],
            "top_k": 5,
            "temperature": 0.1,
            "apply_temporal_decay": self.apply_temporal_decay,
            "decay_half_life_days": self.decay_half_life_days,
        }

        full_answer = ""
        sources = []

        try:
            async with httpx.AsyncClient(timeout=90) as client:
                async with client.stream("POST", f"{API_BASE}/query/stream", json=payload) as response:
                    if response.status_code != 200:
                        raise Exception(f"API error {response.status_code}")
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            try:
                                data = json.loads(line[6:])
                                if not data.get("done"):
                                    full_answer += data.get("token", "")
                                    updated = list(self.messages)
                                    updated[-1] = Message(
                                        role="assistant",
                                        content=full_answer,
                                        is_streaming=True,
                                    )
                                    self.messages = updated
                                    yield
                                else:
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
            self.error_message = str(e)[:80]

        updated = list(self.messages)
        updated[-1] = Message(
            role="assistant",
            content=full_answer or "No response received.",
            sources=sources,
            is_streaming=False,
        )
        self.messages = updated
        self.is_loading = False
        yield


# ─── Helper Components ────────────────────────────────────────────

def status_dot(color: str) -> rx.Component:
    return rx.box(style={
        "width": "7px", "height": "7px",
        "border_radius": "50%",
        "background": color,
        "box_shadow": f"0 0 6px {color}",
        "flex_shrink": "0",
    })


def role_pill_component(role: str) -> rx.Component:
    color = ROLE_COLORS.get(role, PURPLE)
    return rx.box(
        rx.text(f"{ROLE_ICONS.get(role, '🔹')} {role}", font_size="0.72em", font_weight="600", color=color),
        style={"background": f"{color}18", "border": f"1px solid {color}40", "border_radius": "20px", "padding": "2px 10px"},
    )


def source_item(source: Source) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(source.type, font_size="0.85em"),
            rx.vstack(
                rx.text(source.file, font_size="0.73em", font_weight="600", color=TXT, no_of_lines=1),
                rx.text(source.title, font_size="0.67em", color=TXT2, no_of_lines=1),
                spacing="0", align_items="start",
            ),
            spacing="2", align_items="center",
        ),
        style={
            "background": BG2, "border": f"1px solid {BORDER}",
            "border_radius": "8px", "padding": "6px 11px",
            "_hover": {"border_color": BORDER_A},
            "transition": "border-color 0.2s",
        },
    )


def message_bubble(msg: Message) -> rx.Component:
    is_user = msg.role == "user"

    bubble_content = rx.cond(
        msg.is_streaming & (msg.content == ""),
        # Typing dots
        rx.hstack(
            rx.box(style={"width": "7px", "height": "7px", "border_radius": "50%", "background": PURPLE, "animation": "bounce 1.2s 0s infinite ease-in-out"}),
            rx.box(style={"width": "7px", "height": "7px", "border_radius": "50%", "background": BLUE, "animation": "bounce 1.2s 0.2s infinite ease-in-out"}),
            rx.box(style={"width": "7px", "height": "7px", "border_radius": "50%", "background": GREEN, "animation": "bounce 1.2s 0.4s infinite ease-in-out"}),
            spacing="1", align_items="center", padding_y="4px",
        ),
        rx.vstack(
            rx.cond(
                is_user,
                rx.text(msg.content, font_size="0.91em", line_height="1.75", color=TXT),
                rx.markdown(msg.content),
            ),
            rx.cond(
                msg.sources.length() > 0,
                rx.vstack(
                    rx.text("📚 Sources", font_size="0.68em", font_weight="700", color=MUTED, letter_spacing="0.08em"),
                    rx.flex(
                        rx.foreach(msg.sources, source_item),
                        flex_wrap="wrap", gap="6px",
                    ),
                    spacing="2", width="100%",
                    padding_top="0.6em",
                    border_top=f"1px solid {BORDER}",
                    margin_top="0.3em",
                ),
                rx.box(),
            ),
            spacing="1", align_items="start", width="100%",
        ),
    )

    return rx.hstack(
        rx.cond(
            ~is_user,
            rx.box(
                rx.text("🔐"),
                style={"background": f"{PURPLE}22", "border": f"1px solid {PURPLE}44",
                       "border_radius": "50%", "width": "34px", "height": "34px",
                       "display": "flex", "align_items": "center", "justify_content": "center",
                       "flex_shrink": "0", "font_size": "1em"},
            ),
            rx.box(),
        ),
        rx.box(
            bubble_content,
            style={
                "background": rx.cond(is_user, f"{BLUE}14", f"{GREEN}08"),
                "border": rx.cond(is_user, f"1px solid {BLUE}30", f"1px solid {GREEN}20"),
                "border_radius": "16px",
                "border_bottom_right_radius": rx.cond(is_user, "4px", "16px"),
                "border_bottom_left_radius": rx.cond(is_user, "16px", "4px"),
                "padding": "12px 16px",
                "max_width": "78%",
                "min_width": "80px",
                "box_shadow": "0 2px 12px rgba(0,0,0,0.3)",
            },
        ),
        rx.cond(
            is_user,
            rx.box(
                rx.text("👤"),
                style={"background": f"{BLUE}22", "border": f"1px solid {BLUE}44",
                       "border_radius": "50%", "width": "34px", "height": "34px",
                       "display": "flex", "align_items": "center", "justify_content": "center",
                       "flex_shrink": "0", "font_size": "1em"},
            ),
            rx.box(),
        ),
        justify=rx.cond(is_user, "end", "start"),
        align_items="end",
        width="100%",
        spacing="2",
    )


# ─── Sidebar ──────────────────────────────────────────────────────

def sidebar() -> rx.Component:
    return rx.box(
        rx.vstack(
            # Brand
            rx.vstack(
                rx.text("VaultIQ", style={
                    "background": f"linear-gradient(135deg, {PURPLE}, {BLUE}, {GREEN})",
                    "WebkitBackgroundClip": "text",
                    "WebkitTextFillColor": "transparent",
                    "font_size": "1.55em", "font_weight": "800", "letter_spacing": "-0.03em",
                }),
                rx.text("Enterprise Knowledge Search", font_size="0.62em", color=MUTED, letter_spacing="0.08em", text_transform="uppercase"),
                spacing="0", padding_bottom="1.2em",
            ),
            rx.divider(border_color=BORDER),

            # Navigation Tabs
            rx.vstack(
                rx.button(
                    "💬 Chat Assistant",
                    on_click=State.set_tab("chat"),
                    style={
                        "background": rx.cond(State.active_tab == "chat", f"{PURPLE}25", "transparent"),
                        "color": rx.cond(State.active_tab == "chat", TXT, TXT2),
                        "border": rx.cond(State.active_tab == "chat", f"1px solid {BORDER_A}", f"1px solid {BORDER}"),
                        "border_radius": "8px", "width": "100%", "font_size": "0.83em", "font_weight": "600",
                        "cursor": "pointer", "padding": "8px 12px", "justify_content": "start",
                    },
                ),
                rx.button(
                    "⚙️ Data Studio & Recency",
                    on_click=State.set_tab("data_studio"),
                    style={
                        "background": rx.cond(State.active_tab == "data_studio", f"{PURPLE}25", "transparent"),
                        "color": rx.cond(State.active_tab == "data_studio", TXT, TXT2),
                        "border": rx.cond(State.active_tab == "data_studio", f"1px solid {BORDER_A}", f"1px solid {BORDER}"),
                        "border_radius": "8px", "width": "100%", "font_size": "0.83em", "font_weight": "600",
                        "cursor": "pointer", "padding": "8px 12px", "justify_content": "start",
                    },
                ),
                spacing="2", width="100%", padding_y="0.8em",
            ),
            rx.divider(border_color=BORDER),

            # Role
            rx.vstack(
                rx.text("YOUR ROLE", font_size="0.58em", font_weight="700", color=MUTED, letter_spacing="0.12em"),
                rx.select(
                    ROLES, value=State.current_role, on_change=State.set_role,
                    style={
                        "background": CARD, "color": TXT,
                        "border": f"1px solid {BORDER_A}",
                        "border_radius": "10px", "padding": "8px 12px",
                        "width": "100%", "font_size": "0.87em",
                        "_focus": {"outline": f"2px solid {PURPLE}"},
                    },
                ),
                rx.box(
                    rx.text("🔒 ACL Enforced — Role-based filtering active", font_size="0.67em", color=GREEN),
                    style={"background": f"{GREEN}11", "border": f"1px solid {GREEN}30", "border_radius": "6px", "padding": "5px 10px"},
                ),
                spacing="2", align_items="stretch", width="100%", padding_y="0.9em",
            ),
            rx.divider(border_color=BORDER),

            # Status
            rx.vstack(
                rx.text("SYSTEM STATUS", font_size="0.58em", font_weight="700", color=MUTED, letter_spacing="0.12em"),
                rx.cond(
                    State.health_loaded,
                    rx.vstack(
                        rx.hstack(status_dot(GREEN), rx.text(State.qdrant_vectors.to_string() + " vectors · Qdrant", font_size="0.76em", color=TXT2), align_items="center", spacing="2"),
                        rx.hstack(status_dot(BLUE), rx.text(State.bm25_docs.to_string() + " docs · BM25", font_size="0.76em", color=TXT2), align_items="center", spacing="2"),
                        rx.hstack(
                            status_dot(rx.cond(State.llm_available, PURPLE, "#ef4444")),
                            rx.text(rx.cond(State.llm_available, "Groq LLaMA-3 · Ready", "LLM · Offline"), font_size="0.76em", color=TXT2),
                            align_items="center", spacing="2",
                        ),
                        spacing="2", align_items="start", width="100%",
                    ),
                    rx.hstack(rx.spinner(size="1"), rx.text("Connecting...", font_size="0.75em", color=MUTED), align_items="center", spacing="2"),
                ),
                spacing="2", align_items="start", width="100%", padding_y="0.9em",
            ),
            rx.divider(border_color=BORDER),

            # Try asking
            rx.vstack(
                rx.text("TRY ASKING", font_size="0.58em", font_weight="700", color=MUTED, letter_spacing="0.12em"),
                rx.foreach(
                    SAMPLE_QUESTIONS,
                    lambda q: rx.box(
                        rx.text(q, font_size="0.76em", color=TXT2, no_of_lines=2),
                        on_click=State.use_sample(q),
                        style={
                            "background": CARD, "border": f"1px solid {BORDER}",
                            "border_radius": "8px", "padding": "7px 11px",
                            "cursor": "pointer", "width": "100%",
                            "_hover": {"border_color": BORDER_A, "background": HOVER},
                            "transition": "all 0.15s ease",
                        },
                    ),
                ),
                spacing="2", align_items="start", width="100%", padding_y="0.9em",
            ),

            rx.spacer(),

            rx.button(
                "🗑️ Clear Chat", on_click=State.clear_chat,
                style={
                    "background": "transparent", "color": MUTED,
                    "border": f"1px solid {BORDER}", "border_radius": "8px",
                    "padding": "8px 0", "font_size": "0.79em",
                    "cursor": "pointer", "width": "100%",
                    "_hover": {"border_color": "#ef444440", "color": "#ef4444", "background": "#ef444410"},
                    "transition": "all 0.15s ease",
                },
            ),
            spacing="0", align_items="stretch", height="100%",
        ),
        padding="1.3em",
        style={
            "background": BG2, "border_right": f"1px solid {BORDER}",
            "width": "255px", "min_width": "255px", "height": "100vh",
            "position": "fixed", "left": "0", "top": "0",
            "overflow_y": "auto", "z_index": "10",
        },
    )


# ─── Data Studio View ─────────────────────────────────────────────

def data_studio_view() -> rx.Component:
    return rx.vstack(
        # Header
        rx.vstack(
            rx.heading("⚙️ Data Studio & Temporal Recency Engine", font_size="1.5em", font_weight="800", color=TXT),
            rx.text("Manage datasets, configure exponential decay parameters, and handle dataset lifecycles.", font_size="0.85em", color=TXT2),
            spacing="1", align_items="start", padding_bottom="1.5em",
        ),

        # Temporal Decay Configuration Card
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.text("⏳ Temporal Recency Decay Scoring", font_size="1.1em", font_weight="700", color=TXT),
                    rx.box(
                        rx.text("EXPONENTIAL DECAY ACTIVE", font_size="0.65em", font_weight="700", color=GREEN),
                        style={"background": f"{GREEN}15", "border": f"1px solid {GREEN}40", "border_radius": "12px", "padding": "3px 10px"},
                    ),
                    justify="between", width="100%", align_items="center",
                ),
                rx.text(
                    "Prioritizes newly uploaded or updated policies over older ones using an exponential decay function: Score_final = Score_RRF * exp(-lambda * delta_t_days).",
                    font_size="0.8em", color=TXT2, line_height="1.6",
                ),
                rx.hstack(
                    rx.switch(
                        checked=State.apply_temporal_decay,
                        on_change=State.toggle_decay,
                    ),
                    rx.text("Enable Recency Decay Weighting", font_size="0.85em", font_weight="600", color=TXT),
                    spacing="3", align_items="center", padding_y="0.5em",
                ),
                rx.divider(border_color=BORDER),
                rx.vstack(
                    rx.hstack(
                        rx.text("Decay Half-Life (Days):", font_size="0.82em", font_weight="600", color=TXT2),
                        rx.text(State.decay_half_life_days.to_string() + " days", font_size="0.82em", font_weight="700", color=PURPLE),
                        justify="between", width="100%",
                    ),
                    rx.text("Documents older than this half-life receive a 50% score penalty relative to brand new documents.", font_size="0.75em", color=MUTED),
                    spacing="1", width="100%",
                ),
                spacing="3", align_items="start", width="100%",
            ),
            style={
                "background": CARD, "border": f"1px solid {BORDER_A}",
                "border_radius": "14px", "padding": "20px", "width": "100%",
            },
        ),

        # Re-Index Trigger Card
        rx.box(
            rx.vstack(
                rx.heading("🔄 Rebuild Index & Re-Ingest Data", font_size="1.1em", font_weight="700", color=TXT),
                rx.text("Trigger clean re-ingestion of files in data/synthetic/ with latest timestamps and dataset tags.", font_size="0.82em", color=TXT2),
                rx.cond(
                    State.status_message != "",
                    rx.box(
                        rx.text(State.status_message, font_size="0.82em", color=GREEN),
                        style={"background": f"{GREEN}15", "border": f"1px solid {GREEN}30", "border_radius": "8px", "padding": "8px 12px"},
                    ),
                    rx.box(),
                ),
                rx.button(
                    rx.cond(State.is_loading, rx.spinner(size="2"), rx.text("🔄 Trigger Full Re-Index", font_weight="700")),
                    on_click=State.rebuild_index_now,
                    disabled=State.is_loading,
                    style={
                        "background": f"linear-gradient(135deg, {PURPLE}, {BLUE})",
                        "color": TXT, "border": "none", "border_radius": "10px",
                        "padding": "10px 20px", "font_size": "0.88em", "cursor": "pointer",
                    },
                ),
                spacing="3", align_items="start", width="100%",
            ),
            style={
                "background": CARD, "border": f"1px solid {BORDER}",
                "border_radius": "14px", "padding": "20px", "width": "100%", "margin_top": "1.5em",
            },
        ),

        spacing="0", align_items="start", width="100%", padding="2em",
    )


# ─── Empty State ─────────────────────────────────────────────────

def empty_state() -> rx.Component:
    return rx.vstack(
        rx.text("🔐", font_size="3.5em"),
        rx.text("VaultIQ", style={
            "background": f"linear-gradient(135deg, {PURPLE}, {BLUE}, {GREEN})",
            "WebkitBackgroundClip": "text",
            "WebkitTextFillColor": "transparent",
            "font_size": "2.1em", "font_weight": "800", "letter_spacing": "-0.03em",
        }),
        rx.text("Your enterprise knowledge, instantly searchable.", font_size="0.97em", color=TXT2, text_align="center"),
        rx.text("Select a role in the sidebar, then ask anything.", font_size="0.8em", color=MUTED, text_align="center"),
        spacing="3", align_items="center", justify_content="center",
        height="100%", padding="4em 2em",
    )


# ─── Main Page ───────────────────────────────────────────────────

def index() -> rx.Component:
    return rx.box(
        rx.el.style("""
            @keyframes bounce {
                0%, 80%, 100% { transform: translateY(0); opacity: 1; }
                40% { transform: translateY(-6px); opacity: 0.45; }
            }
            * { box-sizing: border-box; }
            body { background: #0a0a0f !important; margin: 0; }
            ::-webkit-scrollbar { width: 5px; }
            ::-webkit-scrollbar-track { background: transparent; }
            ::-webkit-scrollbar-thumb { background: #2a2a3a; border-radius: 3px; }
        """),
        sidebar(),
        # Main content area
        rx.box(
            rx.cond(
                State.active_tab == "data_studio",
                data_studio_view(),
                rx.vstack(
                    # Chat messages area
                    rx.box(
                        rx.cond(
                            State.messages.length() == 0,
                            empty_state(),
                            rx.vstack(
                                rx.foreach(State.messages, message_bubble),
                                spacing="4",
                                align_items="stretch",
                                width="100%",
                                padding="1.5em",
                                padding_bottom="1em",
                            ),
                        ),
                        style={"flex": "1", "overflow_y": "auto", "width": "100%", "scrollbar_width": "thin"},
                    ),
                    # Input bar
                    rx.box(
                        rx.cond(
                            State.error_message != "",
                            rx.box(
                                rx.text(f"⚠️ {State.error_message}", font_size="0.78em", color="#ef4444"),
                                style={"background": "#ef444410", "border": "1px solid #ef444430", "border_radius": "8px", "padding": "6px 12px", "margin_bottom": "0.5em"},
                            ),
                            rx.box(),
                        ),
                        rx.hstack(
                            rx.text_area(
                                value=State.query,
                                on_change=State.set_query,
                                placeholder="Ask anything about your company knowledge base...",
                                style={
                                    "background": CARD, "color": TXT,
                                    "border": f"1px solid {BORDER}",
                                    "border_radius": "12px",
                                    "padding": "13px 15px",
                                    "font_size": "0.9em",
                                    "resize": "none",
                                    "min_height": "50px",
                                    "max_height": "110px",
                                    "flex": "1",
                                    "font_family": "inherit",
                                    "_focus": {"outline": "none", "border_color": PURPLE, "box_shadow": f"0 0 0 3px {PURPLE}22"},
                                    "_placeholder": {"color": MUTED},
                                    "transition": "border-color 0.2s, box-shadow 0.2s",
                                },
                                rows="1",
                            ),
                            rx.button(
                                rx.cond(State.is_loading, rx.spinner(size="2"), rx.text("↑", font_size="1.3em", font_weight="700")),
                                on_click=State.send_query,
                                disabled=State.is_loading,
                                style={
                                    "background": rx.cond(State.is_loading, CARD, f"linear-gradient(135deg, {PURPLE}, {BLUE})"),
                                    "color": TXT,
                                    "border": "none", "border_radius": "12px",
                                    "width": "50px", "height": "50px",
                                    "cursor": rx.cond(State.is_loading, "not-allowed", "pointer"),
                                    "flex_shrink": "0",
                                    "box_shadow": rx.cond(State.is_loading, "none", f"0 4px 16px {PURPLE}44"),
                                    "transition": "all 0.2s ease",
                                    "_hover": {"transform": rx.cond(State.is_loading, "none", "scale(1.06)")},
                                },
                            ),
                            align_items="end", spacing="3",
                        ),
                        rx.hstack(
                            rx.text("Role:", font_size="0.66em", color=MUTED),
                            role_pill_component(State.current_role),
                            rx.text("· Recency Decay Weighting:", font_size="0.66em", color=MUTED),
                            rx.cond(State.apply_temporal_decay, rx.text("Active (180d)", font_size="0.66em", color=GREEN), rx.text("Disabled", font_size="0.66em", color=MUTED)),
                            spacing="1", align_items="center", padding_top="0.45em",
                        ),
                        style={"background": BG, "border_top": f"1px solid {BORDER}", "padding": "1.1em 1.4em"},
                    ),
                    spacing="0", height="100vh", align_items="stretch",
                ),
            ),
            style={
                "margin_left": "255px", "flex": "1",
                "display": "flex", "flex_direction": "column",
                "background": BG, "min_height": "100vh",
            },
        ),
        on_mount=State.load_health,
        style={
            "display": "flex", "min_height": "100vh",
            "background": BG, "color": TXT,
            "font_family": "'Inter', 'system-ui', sans-serif",
        },
    )


app = rx.App(
    theme=rx.theme(appearance="dark", accent_color="violet", radius="medium"),
    head_components=[
        rx.el.link(rel="preconnect", href="https://fonts.googleapis.com"),
        rx.el.link(rel="preconnect", href="https://fonts.gstatic.com", crossorigin=""),
        rx.el.link(href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap", rel="stylesheet"),
    ],
)

app.add_page(index, route="/", title="VaultIQ — Enterprise Knowledge Search")

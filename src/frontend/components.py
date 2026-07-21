"""
VaultIQ — Beautiful Reflex Frontend
Dark-themed enterprise RAG chat interface with streaming support.
"""

import reflex as rx
from .state import State, Message, Source, ROLES, ROLE_COLORS, ROLE_ICONS, SAMPLE_QUESTIONS


# ─── Design Tokens ────────────────────────────────────────────────

COLORS = {
    "bg_primary": "#0a0a0f",
    "bg_secondary": "#111118",
    "bg_card": "#16161f",
    "bg_hover": "#1e1e2a",
    "border": "#2a2a3a",
    "border_active": "#7c3aed",
    "text_primary": "#f0f0f8",
    "text_secondary": "#8888aa",
    "text_muted": "#55556a",
    "accent_primary": "#7c3aed",
    "accent_glow": "#9d5ef5",
    "accent_blue": "#3b82f6",
    "accent_green": "#10b981",
    "user_bubble": "#1a1a35",
    "user_border": "#3b4080",
    "assistant_bubble": "#0f1a20",
    "assistant_border": "#1a3040",
}


# ─── Reusable Components ──────────────────────────────────────────

def gradient_text(text: str, size: str = "1.5em") -> rx.Component:
    return rx.text(
        text,
        style={
            "background": "linear-gradient(135deg, #7c3aed 0%, #3b82f6 50%, #10b981 100%)",
            "WebkitBackgroundClip": "text",
            "WebkitTextFillColor": "transparent",
            "backgroundClip": "text",
            "font_size": size,
            "font_weight": "800",
            "letter_spacing": "-0.02em",
        },
    )


def role_badge(role: str) -> rx.Component:
    return rx.badge(
        f"{ROLE_ICONS.get(role, '🔹')} {role}",
        style={
            "background": f"{ROLE_COLORS.get(role, '#7c3aed')}22",
            "color": ROLE_COLORS.get(role, "#7c3aed"),
            "border": f"1px solid {ROLE_COLORS.get(role, '#7c3aed')}44",
            "border_radius": "20px",
            "padding": "2px 10px",
            "font_size": "0.75em",
            "font_weight": "600",
        },
    )


def source_card(source: Source) -> rx.Component:
    icon = {"wiki": "📄", "pdf": "📋", "slack": "💬", "csv": "📊"}.get(
        source.type, "📄"
    )
    return rx.box(
        rx.hstack(
            rx.text(icon, font_size="1em"),
            rx.vstack(
                rx.text(
                    source.file,
                    font_size="0.78em",
                    font_weight="600",
                    color=COLORS["text_primary"],
                    no_of_lines=1,
                ),
                rx.text(
                    source.title,
                    font_size="0.7em",
                    color=COLORS["text_secondary"],
                    no_of_lines=1,
                ),
                spacing="0",
                align_items="start",
            ),
            spacing="2",
            align_items="center",
        ),
        style={
            "background": COLORS["bg_secondary"],
            "border": f"1px solid {COLORS['border']}",
            "border_radius": "8px",
            "padding": "8px 12px",
            "cursor": "default",
            "_hover": {"border_color": COLORS["border_active"]},
            "transition": "border-color 0.2s",
        },
    )


def typing_indicator() -> rx.Component:
    return rx.hstack(
        rx.box(
            style={
                "width": "8px",
                "height": "8px",
                "border_radius": "50%",
                "background": COLORS["accent_primary"],
                "animation": "pulse 1s ease-in-out infinite",
            }
        ),
        rx.box(
            style={
                "width": "8px",
                "height": "8px",
                "border_radius": "50%",
                "background": COLORS["accent_blue"],
                "animation": "pulse 1s ease-in-out 0.2s infinite",
            }
        ),
        rx.box(
            style={
                "width": "8px",
                "height": "8px",
                "border_radius": "50%",
                "background": COLORS["accent_green"],
                "animation": "pulse 1s ease-in-out 0.4s infinite",
            }
        ),
        spacing="1",
        align_items="center",
    )


def chat_message(message: Message) -> rx.Component:
    is_user = message.role == "user"

    bubble = rx.box(
        rx.cond(
            is_user,
            # User message
            rx.text(
                message.content,
                style={
                    "color": COLORS["text_primary"],
                    "font_size": "0.92em",
                    "line_height": "1.7",
                    "white_space": "pre-wrap",
                },
            ),
            # Assistant message
            rx.vstack(
                rx.cond(
                    message.is_streaming & (message.content == ""),
                    typing_indicator(),
                    rx.markdown(
                        message.content,
                        component_map={
                            "p": lambda text: rx.text(
                                text,
                                style={
                                    "color": COLORS["text_primary"],
                                    "font_size": "0.92em",
                                    "line_height": "1.7",
                                    "margin_bottom": "0.5em",
                                },
                            ),
                        },
                    ),
                ),
                # Sources
                rx.cond(
                    message.sources.length() > 0,
                    rx.vstack(
                        rx.hstack(
                            rx.text(
                                "📚 Sources",
                                font_size="0.75em",
                                font_weight="700",
                                color=COLORS["text_muted"],
                                letter_spacing="0.08em",
                            ),
                            rx.divider(
                                style={
                                    "border_color": COLORS["border"],
                                    "flex": "1",
                                }
                            ),
                        ),
                        rx.flex(
                            rx.foreach(message.sources, source_card),
                            flex_wrap="wrap",
                            gap="6px",
                        ),
                        spacing="2",
                        align_items="stretch",
                        width="100%",
                        padding_top="0.75em",
                    ),
                    rx.box(),
                ),
                spacing="3",
                align_items="start",
                width="100%",
            ),
        ),
        style={
            "background": COLORS["user_bubble"] if is_user else COLORS["assistant_bubble"],
            "border": f"1px solid {COLORS['user_border'] if is_user else COLORS['assistant_border']}",
            "border_radius": "16px",
            "border_bottom_right_radius": "4px" if is_user else "16px",
            "border_bottom_left_radius": "4px" if not is_user else "16px",
            "padding": "14px 18px",
            "max_width": "82%",
            "min_width": "100px",
            "box_shadow": "0 2px 12px rgba(0,0,0,0.3)",
        },
    )

    return rx.hstack(
        rx.cond(
            is_user,
            rx.box(),
            rx.box(
                rx.text("🔐", font_size="1.1em"),
                style={
                    "background": "linear-gradient(135deg, #7c3aed22, #3b82f622)",
                    "border": f"1px solid {COLORS['border']}",
                    "border_radius": "50%",
                    "width": "32px",
                    "height": "32px",
                    "display": "flex",
                    "align_items": "center",
                    "justify_content": "center",
                    "flex_shrink": "0",
                },
            ),
        ),
        bubble,
        rx.cond(
            is_user,
            rx.box(
                rx.text("👤", font_size="1.1em"),
                style={
                    "background": f"{COLORS['user_border']}33",
                    "border": f"1px solid {COLORS['user_border']}",
                    "border_radius": "50%",
                    "width": "32px",
                    "height": "32px",
                    "display": "flex",
                    "align_items": "center",
                    "justify_content": "center",
                    "flex_shrink": "0",
                },
            ),
            rx.box(),
        ),
        justify="end" if is_user else "start",
        align_items="end",
        width="100%",
        spacing="2",
    )


def sidebar() -> rx.Component:
    return rx.box(
        rx.vstack(
            # Logo / Brand
            rx.vstack(
                gradient_text("VaultIQ", "1.6em"),
                rx.text(
                    "Enterprise RAG · AI Knowledge Search",
                    font_size="0.68em",
                    color=COLORS["text_muted"],
                    letter_spacing="0.06em",
                    text_transform="uppercase",
                ),
                spacing="0",
                align_items="start",
                padding_bottom="1.5em",
            ),

            rx.divider(border_color=COLORS["border"]),

            # Role Selector
            rx.vstack(
                rx.text(
                    "YOUR ROLE",
                    font_size="0.65em",
                    font_weight="700",
                    color=COLORS["text_muted"],
                    letter_spacing="0.1em",
                ),
                rx.select(
                    ROLES,
                    value=State.current_role,
                    on_change=State.set_role,
                    style={
                        "background": COLORS["bg_card"],
                        "color": COLORS["text_primary"],
                        "border": f"1px solid {COLORS['border_active']}",
                        "border_radius": "10px",
                        "padding": "8px 12px",
                        "width": "100%",
                        "font_size": "0.88em",
                        "cursor": "pointer",
                        "_focus": {"outline": f"2px solid {COLORS['accent_primary']}"},
                    },
                ),
                rx.box(
                    rx.text(
                        "🔒 ACL Enforced",
                        font_size="0.7em",
                        color=COLORS["accent_green"],
                    ),
                    style={
                        "background": f"{COLORS['accent_green']}11",
                        "border": f"1px solid {COLORS['accent_green']}33",
                        "border_radius": "6px",
                        "padding": "4px 10px",
                    },
                ),
                spacing="2",
                align_items="stretch",
                width="100%",
                padding_y="1em",
            ),

            rx.divider(border_color=COLORS["border"]),

            # System Info
            rx.vstack(
                rx.text(
                    "SYSTEM STATUS",
                    font_size="0.65em",
                    font_weight="700",
                    color=COLORS["text_muted"],
                    letter_spacing="0.1em",
                ),
                rx.cond(
                    State.health_loaded,
                    rx.vstack(
                        rx.hstack(
                            rx.box(
                                style={
                                    "width": "8px",
                                    "height": "8px",
                                    "border_radius": "50%",
                                    "background": COLORS["accent_green"],
                                    "box_shadow": f"0 0 8px {COLORS['accent_green']}",
                                }
                            ),
                            rx.text(
                                State.qdrant_vectors.to_string() + " Vectors · Qdrant",
                                font_size="0.78em",
                                color=COLORS["text_secondary"],
                            ),
                            align_items="center",
                            spacing="2",
                        ),
                        rx.hstack(
                            rx.box(
                                style={
                                    "width": "8px",
                                    "height": "8px",
                                    "border_radius": "50%",
                                    "background": COLORS["accent_blue"],
                                    "box_shadow": f"0 0 8px {COLORS['accent_blue']}",
                                }
                            ),
                            rx.text(
                                State.bm25_docs.to_string() + " Docs · BM25",
                                font_size="0.78em",
                                color=COLORS["text_secondary"],
                            ),
                            align_items="center",
                            spacing="2",
                        ),
                        rx.hstack(
                            rx.box(
                                style={
                                    "width": "8px",
                                    "height": "8px",
                                    "border_radius": "50%",
                                    "background": rx.cond(
                                        State.llm_available,
                                        COLORS["accent_primary"],
                                        "#ef4444",
                                    ),
                                    "box_shadow": rx.cond(
                                        State.llm_available,
                                        f"0 0 8px {COLORS['accent_primary']}",
                                        "0 0 8px #ef4444",
                                    ),
                                }
                            ),
                            rx.text(
                                rx.cond(State.llm_available, "Groq LLM · Ready", "LLM · Offline"),
                                font_size="0.78em",
                                color=COLORS["text_secondary"],
                            ),
                            align_items="center",
                            spacing="2",
                        ),
                        spacing="2",
                        align_items="start",
                        width="100%",
                    ),
                    rx.text(
                        "Connecting...",
                        font_size="0.78em",
                        color=COLORS["text_muted"],
                    ),
                ),
                spacing="2",
                align_items="start",
                width="100%",
                padding_y="1em",
            ),

            rx.divider(border_color=COLORS["border"]),

            # Quick Questions
            rx.vstack(
                rx.text(
                    "QUICK QUESTIONS",
                    font_size="0.65em",
                    font_weight="700",
                    color=COLORS["text_muted"],
                    letter_spacing="0.1em",
                ),
                rx.foreach(
                    SAMPLE_QUESTIONS,
                    lambda q: rx.box(
                        rx.text(q, font_size="0.78em", color=COLORS["text_secondary"], no_of_lines=2),
                        on_click=State.use_sample(q),
                        style={
                            "background": COLORS["bg_card"],
                            "border": f"1px solid {COLORS['border']}",
                            "border_radius": "8px",
                            "padding": "8px 12px",
                            "cursor": "pointer",
                            "width": "100%",
                            "_hover": {
                                "border_color": COLORS["border_active"],
                                "background": COLORS["bg_hover"],
                                "color": COLORS["text_primary"],
                            },
                            "transition": "all 0.15s ease",
                        },
                    ),
                ),
                spacing="2",
                align_items="start",
                width="100%",
                padding_y="1em",
            ),

            rx.spacer(),

            # Clear Chat Button
            rx.button(
                "🗑️ Clear Chat",
                on_click=State.clear_chat,
                style={
                    "background": "transparent",
                    "color": COLORS["text_muted"],
                    "border": f"1px solid {COLORS['border']}",
                    "border_radius": "8px",
                    "padding": "8px 16px",
                    "font_size": "0.8em",
                    "cursor": "pointer",
                    "width": "100%",
                    "_hover": {
                        "border_color": "#ef444444",
                        "color": "#ef4444",
                        "background": "#ef444411",
                    },
                    "transition": "all 0.15s ease",
                },
            ),

            spacing="0",
            align_items="stretch",
            height="100%",
            padding="1.5em",
        ),
        style={
            "background": COLORS["bg_secondary"],
            "border_right": f"1px solid {COLORS['border']}",
            "width": "260px",
            "min_width": "260px",
            "height": "100vh",
            "position": "fixed",
            "left": "0",
            "top": "0",
            "overflow_y": "auto",
            "z_index": "10",
        },
    )


def empty_state() -> rx.Component:
    return rx.vstack(
        rx.box(
            gradient_text("🔐", "3.5em"),
            style={
                "animation": "float 3s ease-in-out infinite",
            },
        ),
        gradient_text("VaultIQ", "2.2em"),
        rx.text(
            "Ask anything about your company knowledge base.",
            font_size="1em",
            color=COLORS["text_secondary"],
            text_align="center",
        ),
        rx.text(
            "Your access is controlled by your selected role.",
            font_size="0.82em",
            color=COLORS["text_muted"],
            text_align="center",
        ),
        spacing="3",
        align_items="center",
        justify_content="center",
        height="100%",
        padding="3em",
    )


def chat_area() -> rx.Component:
    return rx.box(
        rx.cond(
            State.messages.length() == 0,
            empty_state(),
            rx.vstack(
                rx.foreach(State.messages, chat_message),
                spacing="4",
                align_items="stretch",
                width="100%",
                padding="1.5em",
                padding_bottom="2em",
            ),
        ),
        style={
            "flex": "1",
            "overflow_y": "auto",
            "scrollbar_width": "thin",
            "scrollbar_color": f"{COLORS['border']} transparent",
        },
        id="chat-scroll",
    )


def input_bar() -> rx.Component:
    return rx.box(
        rx.cond(
            State.error_message != "",
            rx.box(
                rx.text(
                    f"⚠️ {State.error_message}",
                    font_size="0.8em",
                    color="#ef4444",
                ),
                style={
                    "background": "#ef444411",
                    "border": "1px solid #ef444433",
                    "border_radius": "8px",
                    "padding": "8px 14px",
                    "margin_bottom": "0.75em",
                },
            ),
            rx.box(),
        ),
        rx.hstack(
            rx.text_area(
                value=State.query,
                on_change=State.set_query,
                placeholder="Ask a question about your company...",
                on_key_down=lambda e: rx.cond(
                    e == "Enter",
                    State.send_query(),
                    rx.noop(),
                ),
                style={
                    "background": COLORS["bg_card"],
                    "color": COLORS["text_primary"],
                    "border": f"1px solid {COLORS['border']}",
                    "border_radius": "12px",
                    "padding": "14px 16px",
                    "font_size": "0.92em",
                    "resize": "none",
                    "min_height": "52px",
                    "max_height": "120px",
                    "flex": "1",
                    "_focus": {
                        "outline": "none",
                        "border_color": COLORS["accent_primary"],
                        "box_shadow": f"0 0 0 2px {COLORS['accent_primary']}33",
                    },
                    "_placeholder": {"color": COLORS["text_muted"]},
                    "transition": "border-color 0.2s, box-shadow 0.2s",
                },
                rows="1",
            ),
            rx.button(
                rx.cond(
                    State.is_loading,
                    rx.spinner(size="3"),
                    rx.text("→", font_size="1.2em", font_weight="700"),
                ),
                on_click=State.send_query,
                disabled=State.is_loading,
                style={
                    "background": rx.cond(
                        State.is_loading,
                        COLORS["bg_card"],
                        f"linear-gradient(135deg, {COLORS['accent_primary']}, {COLORS['accent_blue']})",
                    ),
                    "color": COLORS["text_primary"],
                    "border": "none",
                    "border_radius": "12px",
                    "width": "52px",
                    "height": "52px",
                    "cursor": rx.cond(State.is_loading, "not-allowed", "pointer"),
                    "flex_shrink": "0",
                    "box_shadow": rx.cond(
                        State.is_loading,
                        "none",
                        f"0 4px 16px {COLORS['accent_primary']}44",
                    ),
                    "transition": "all 0.2s ease",
                    "_hover": {
                        "transform": rx.cond(State.is_loading, "none", "scale(1.05)"),
                        "box_shadow": rx.cond(
                            State.is_loading,
                            "none",
                            f"0 6px 20px {COLORS['accent_primary']}66",
                        ),
                    },
                    "_active": {"transform": "scale(0.97)"},
                },
            ),
            align_items="end",
            spacing="3",
        ),
        rx.hstack(
            rx.text("Press", font_size="0.68em", color=COLORS["text_muted"]),
            rx.kbd("Enter", style={"font_size": "0.65em", "background": COLORS["bg_card"]}),
            rx.text("to send ·", font_size="0.68em", color=COLORS["text_muted"]),
            role_badge(State.current_role),
            rx.text("access", font_size="0.68em", color=COLORS["text_muted"]),
            spacing="1",
            align_items="center",
            padding_top="0.5em",
        ),
        style={
            "background": COLORS["bg_primary"],
            "border_top": f"1px solid {COLORS['border']}",
            "padding": "1.25em 1.5em",
            "position": "sticky",
            "bottom": "0",
        },
    )


def index() -> rx.Component:
    return rx.box(
        rx.script("""
            @keyframes float {
                0%, 100% { transform: translateY(0px); }
                50% { transform: translateY(-10px); }
            }
            @keyframes pulse {
                0%, 100% { opacity: 1; transform: scale(1); }
                50% { opacity: 0.5; transform: scale(0.8); }
            }
        """),
        sidebar(),
        rx.box(
            rx.vstack(
                chat_area(),
                input_bar(),
                spacing="0",
                height="100vh",
                align_items="stretch",
            ),
            style={
                "margin_left": "260px",
                "flex": "1",
                "display": "flex",
                "flex_direction": "column",
                "background": COLORS["bg_primary"],
            },
        ),
        on_mount=State.load_health,
        style={
            "display": "flex",
            "min_height": "100vh",
            "background": COLORS["bg_primary"],
            "color": COLORS["text_primary"],
            "font_family": "'Inter', system-ui, -apple-system, sans-serif",
        },
    )

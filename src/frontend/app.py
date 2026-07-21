"""
VaultIQ Reflex App — Entry Point
"""

import reflex as rx
from .components import index
from .state import State

app = rx.App(
    style={
        "*": {
            "box_sizing": "border-box",
            "margin": "0",
            "padding": "0",
        },
        "body": {
            "background": "#0a0a0f",
            "color": "#f0f0f8",
        },
        "::selection": {
            "background": "#7c3aed44",
        },
        "::-webkit-scrollbar": {
            "width": "6px",
        },
        "::-webkit-scrollbar-track": {
            "background": "transparent",
        },
        "::-webkit-scrollbar-thumb": {
            "background": "#2a2a3a",
            "border_radius": "3px",
        },
    },
    theme=rx.theme(
        appearance="dark",
        accent_color="violet",
        radius="medium",
    ),
    head_components=[
        rx.el.link(
            rel="preconnect",
            href="https://fonts.googleapis.com",
        ),
        rx.el.link(
            rel="preconnect",
            href="https://fonts.gstatic.com",
            crossorigin="",
        ),
        rx.el.link(
            href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap",
            rel="stylesheet",
        ),
    ],
)

app.add_page(index, route="/", title="VaultIQ — Enterprise Knowledge Search")

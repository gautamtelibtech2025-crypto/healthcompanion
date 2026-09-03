"""Reusable NiceGUI components for Health Companion."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from nicegui import ui

from config import APP_NAME, APP_TAGLINE


def editorial_header(title: str, subtitle: str) -> None:
    """Render a publication-style section header."""
    with ui.column().classes("gap-2 w-full"):
        ui.label(APP_NAME.upper()).classes("text-xs tracking-widest font-semibold hc-accent")
        ui.label(title).classes("hc-serif text-5xl md:text-6xl leading-tight")
        ui.label(subtitle).classes("text-base md:text-lg hc-muted max-w-3xl leading-7")


def card(classes: str = ""):
    """Return a styled card context manager."""
    return ui.card().classes(f"hc-card p-6 {classes}".strip())


def flat_card(classes: str = ""):
    """Return a flatter card context manager."""
    return ui.card().classes(f"hc-card-flat p-5 {classes}".strip())


def primary_button(label: str, on_click: Callable[..., Any] | None = None, icon: str | None = None):
    """Create a primary action button."""
    return ui.button(label, on_click=on_click, icon=icon).classes("hc-button px-5 py-3")


def secondary_button(label: str, on_click: Callable[..., Any] | None = None, icon: str | None = None):
    """Create a secondary action button."""
    return ui.button(label, on_click=on_click, icon=icon).classes("hc-button-secondary px-5 py-3")


def sidebar(current_step: str) -> None:
    """Render the professional sidebar."""
    steps = [
        ("AI Settings", "/connect"),
        ("Adaptive Assessment", "/patient"),
        ("Clinical Report", "/report"),
    ]
    sidebar_container = ui.element("aside").classes("hc-sidebar w-72 p-6")

    with sidebar_container:
        with ui.column().classes("hc-sidebar-brand gap-1 pr-10"):
            ui.label(APP_NAME).classes("hc-serif text-3xl")
            ui.label(APP_TAGLINE).classes("text-sm hc-muted leading-6")
        ui.label("Gemini is loaded automatically from .env.").classes(
            "hc-sidebar-helper text-xs hc-muted leading-5 mt-6 mb-5"
        )
        with ui.row().classes("hc-sidebar-nav gap-2"):
            for step, route in steps:
                active = step == current_step
                with ui.button(
                    step,
                    on_click=lambda target=route: ui.navigate.to(target),
                    icon="radio_button_checked" if active else "radio_button_unchecked",
                ).classes(
                    "hc-sidebar-nav-item w-full justify-start text-left px-4 py-3 mb-2 rounded-xl border-none shadow-none "
                    + ("hc-nav-active" if active else "hc-nav-item")
                ):
                    pass
        ui.space().classes("hc-sidebar-spacer")
        ui.separator().classes("hc-sidebar-divider my-5")
        ui.label("No API key is exposed in the interface.").classes(
            "hc-sidebar-footer text-xs hc-muted leading-5"
        )


def metric(label: str, value: str, caption: str = "") -> None:
    """Render a small report metric."""
    with flat_card("min-w-44"):
        ui.label(label).classes("text-xs uppercase tracking-widest hc-muted")
        ui.label(value).classes("hc-serif text-3xl mt-1")
        if caption:
            ui.label(caption).classes("text-xs hc-muted mt-1")

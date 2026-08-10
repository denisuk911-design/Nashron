from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DesignTokens:
    font_family: str = "Segoe UI"
    radius_sm: int = 8
    radius_md: int = 12
    radius_lg: int = 16
    panel_width: int = 292
    inspector_width: int = 312
    animation_fast_ms: int = 160
    animation_normal_ms: int = 200


TOKENS = DesignTokens()

COLORS = {
    "bg": "#0f141b",
    "surface": "#151b23",
    "surface_alt": "#1b232e",
    "surface_hover": "#222c38",
    "line": "#2a3442",
    "line_soft": "#202936",
    "text": "#eef2f7",
    "muted": "#a0a9b6",
    "muted_2": "#747f8d",
    "cyan": "#58c4dd",
    "cyan_dark": "#2792aa",
    "violet": "#7367f0",
    "violet_dark": "#5146bf",
    "green": "#54d18f",
    "amber": "#e0b15c",
    "red": "#e06c75",
    "user_bubble": "#263348",
    "roman_bubble": "#182330",
    "petr_bubble": "#172b24",
}

"""Application configuration for Health Companion."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


APP_NAME = "Health Companion"
APP_TAGLINE = "Adaptive Clinical Assessment System"
GEMINI_API_KEY_ENV = "GEMINI_API_KEY"

AI_RESPONSE_STYLE_OPTIONS = ("Professional Medical", "Simple", "Detailed", "Technical")
AI_OUTPUT_TOKEN_OPTIONS = (1024, 2048, 4096, 8192)
DEFAULT_AI_TEMPERATURE = 0.3
DEFAULT_AI_MAX_OUTPUT_TOKENS = 2048
DEFAULT_AI_RESPONSE_STYLE = "Professional Medical"


def get_gemini_api_key() -> str:
    """Read the Gemini API key from the process environment."""
    return os.getenv(GEMINI_API_KEY_ENV, "").strip()


@dataclass(frozen=True)
class UiPalette:
    """Shared design tokens used by the NiceGUI interface."""

    background: str = "#FFFFFF"
    card: str = "#FFFFFF"
    text: str = "#1F2937"
    secondary_text: str = "#64748B"
    accent: str = "#5B86AD"
    border: str = "#E5E7EB"
    success: str = "#2E5E4E"
    warning: str = "#8A5A10"
    danger: str = "#8B2F2F"


PALETTE = UiPalette()


DISCLAIMER = (
    "This report is an AI-assisted preliminary assessment for educational and "
    "informational use. It is not a diagnosis, prescription, or replacement for "
    "care from a licensed medical professional."
)

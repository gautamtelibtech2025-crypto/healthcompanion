"""Normalize Gemini output into report sections for display and export."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from config import DISCLAIMER
from prompt_builder import REPORT_SECTIONS


@dataclass(frozen=True)
class ReportSection:
    """A single formatted health report section."""

    title: str
    content: str


def _extract_json(raw_text: str) -> dict[str, str]:
    cleaned = raw_text.strip()
    fenced_match = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.DOTALL | re.IGNORECASE)
    if fenced_match:
        cleaned = fenced_match.group(1).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start : end + 1]
    parsed = json.loads(cleaned)
    if not isinstance(parsed, dict):
        raise ValueError("Gemini response did not contain a JSON object.")
    return {str(key): _stringify(value) for key, value in parsed.items()}


def _stringify(value: object) -> str:
    if isinstance(value, list):
        return "\n".join(f"- {item}" for item in value)
    if isinstance(value, dict):
        return "\n".join(f"{key}: {item}" for key, item in value.items())
    return str(value).strip()


def format_report(raw_text: str, patient: dict[str, object]) -> list[ReportSection]:
    """Convert raw Gemini JSON into ordered report sections with fallbacks."""
    try:
        parsed = _extract_json(raw_text)
    except Exception:
        parsed = _fallback_report(raw_text, patient)

    sections: list[ReportSection] = []
    for title in REPORT_SECTIONS:
        content = parsed.get(title, "").strip()
        if not content:
            content = _fallback_content(title, patient)
        sections.append(ReportSection(title=title, content=content))
    return sections


def sections_to_markdown(sections: list[ReportSection]) -> str:
    """Render report sections as clean Markdown."""
    return "\n\n".join(f"## {section.title}\n\n{section.content}" for section in sections)


def _fallback_report(raw_text: str, patient: dict[str, object]) -> dict[str, str]:
    return {
        "Patient Summary": (
            f"{patient.get('full_name')} is a {patient.get('age')}-year-old patient "
            f"reporting {patient.get('primary_concern', 'a health concern')}."
        ),
        "Clinical Findings": raw_text.strip() or "The assessment could not be fully structured.",
        "Risk Score": f"{patient.get('risk_level', 'Moderate')} preliminary risk based on provided information.",
        "Medical Disclaimer": DISCLAIMER,
    }


def _fallback_content(title: str, patient: dict[str, object]) -> str:
    if title == "Medical Disclaimer":
        return DISCLAIMER
    if title == "Risk Score":
        return f"{patient.get('risk_level', 'Moderate')} preliminary risk based on provided information."
    return "No specific details were returned for this section. Please review with a qualified clinician."

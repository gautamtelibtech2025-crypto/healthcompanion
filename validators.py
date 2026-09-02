"""Validation utilities for patient assessment data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ValidationResult:
    """Result returned by patient form validation."""

    is_valid: bool
    errors: dict[str, str]


REQUIRED_TEXT_FIELDS = {
    "full_name": "Full name",
    "gender": "Gender",
    "symptoms": "Symptoms",
    "duration": "Duration",
    "medical_history": "Medical history",
    "current_medication": "Current medication",
    "allergies": "Allergies",
    "smoking": "Smoking status",
    "alcohol": "Alcohol use",
}


def _is_blank(value: Any) -> bool:
    return value is None or str(value).strip() == ""


def validate_patient_data(data: dict[str, Any]) -> ValidationResult:
    """Validate patient form data and return user-friendly errors."""
    errors: dict[str, str] = {}

    for field, label in REQUIRED_TEXT_FIELDS.items():
        if _is_blank(data.get(field)):
            errors[field] = f"{label} is required."

    name = str(data.get("full_name", "")).strip()
    if name and len(name) < 2:
        errors["full_name"] = "Please enter a complete name."

    try:
        age = int(data.get("age", 0))
        if age < 1 or age > 120:
            errors["age"] = "Age must be between 1 and 120."
    except (TypeError, ValueError):
        errors["age"] = "Age must be a valid number."

    try:
        height = float(data.get("height_cm", 0))
        if height < 45 or height > 260:
            errors["height_cm"] = "Height must be between 45 cm and 260 cm."
    except (TypeError, ValueError):
        errors["height_cm"] = "Height must be a valid number."

    try:
        weight = float(data.get("weight_kg", 0))
        if weight < 2 or weight > 350:
            errors["weight_kg"] = "Weight must be between 2 kg and 350 kg."
    except (TypeError, ValueError):
        errors["weight_kg"] = "Weight must be a valid number."

    symptoms = str(data.get("symptoms", "")).strip()
    if symptoms and len(symptoms) < 10:
        errors["symptoms"] = "Please describe symptoms in at least 10 characters."

    return ValidationResult(is_valid=not errors, errors=errors)


def validate_api_key(api_key: str) -> ValidationResult:
    """Validate the Gemini API key format enough for local development setup."""
    key = api_key.strip()
    errors: dict[str, str] = {}
    if not key:
        errors["api_key"] = "Gemini API key is required."
    elif len(key) < 20:
        errors["api_key"] = "The API key looks too short. Please check it and try again."
    return ValidationResult(is_valid=not errors, errors=errors)

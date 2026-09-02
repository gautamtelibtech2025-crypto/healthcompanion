"""BMI and risk helper functions."""

from __future__ import annotations


def calculate_bmi(height_cm: float, weight_kg: float) -> float:
    """Return BMI rounded to one decimal place."""
    if height_cm <= 0:
        raise ValueError("Height must be greater than zero.")
    if weight_kg <= 0:
        raise ValueError("Weight must be greater than zero.")
    height_m = height_cm / 100
    return round(weight_kg / (height_m * height_m), 1)


def bmi_category(bmi: float) -> str:
    """Classify BMI using common adult BMI ranges."""
    if bmi < 18.5:
        return "Underweight"
    if bmi < 25:
        return "Healthy range"
    if bmi < 30:
        return "Overweight"
    return "Obesity range"


def estimate_risk_level(age: int, bmi: float, has_bp: bool, has_diabetes: bool, symptom_duration: str) -> str:
    """Estimate a simple front-end risk level before AI review."""
    score = 0
    if age >= 60:
        score += 2
    elif age >= 45:
        score += 1
    if bmi < 18.5 or bmi >= 30:
        score += 1
    if has_bp:
        score += 1
    if has_diabetes:
        score += 1
    if any(word in symptom_duration.lower() for word in ("week", "month", "year")):
        score += 1

    if score >= 4:
        return "High"
    if score >= 2:
        return "Moderate"
    return "Low"

from bmi import bmi_category, calculate_bmi, estimate_risk_level


def test_calculate_bmi_rounds_to_one_decimal() -> None:
    assert calculate_bmi(170, 65) == 22.5


def test_bmi_category() -> None:
    assert bmi_category(17.9) == "Underweight"
    assert bmi_category(22.0) == "Healthy range"
    assert bmi_category(27.5) == "Overweight"
    assert bmi_category(31.0) == "Obesity range"


def test_estimate_risk_level_high_when_multiple_risks() -> None:
    assert estimate_risk_level(65, 31.0, True, True, "two weeks") == "High"

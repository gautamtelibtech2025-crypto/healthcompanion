from validators import validate_api_key, validate_patient_data


def valid_patient() -> dict[str, object]:
    return {
        "full_name": "Asha Rao",
        "age": 32,
        "gender": "Female",
        "height_cm": 162,
        "weight_kg": 58,
        "symptoms": "Mild fever and fatigue",
        "duration": "Two days",
        "medical_history": "None reported",
        "current_medication": "None reported",
        "allergies": "None reported",
        "smoking": "Never",
        "alcohol": "Rarely",
    }


def test_valid_patient_data_passes() -> None:
    result = validate_patient_data(valid_patient())
    assert result.is_valid
    assert result.errors == {}


def test_invalid_patient_data_collects_errors() -> None:
    data = valid_patient()
    data["age"] = 140
    data["symptoms"] = "Pain"
    result = validate_patient_data(data)
    assert not result.is_valid
    assert "age" in result.errors
    assert "symptoms" in result.errors


def test_validate_api_key_rejects_short_key() -> None:
    result = validate_api_key("abc")
    assert not result.is_valid
    assert "api_key" in result.errors

from report_formatter import format_report, sections_to_markdown


def test_format_report_orders_sections_from_json() -> None:
    patient = {"full_name": "Asha Rao", "age": 32, "risk_level": "Low"}
    raw = '{"Patient Summary": "Summary text", "Risk Score": "Low risk", "Medical Disclaimer": "Disclaimer"}'
    sections = format_report(raw, patient)
    assert sections[0].title == "Patient Summary"
    assert sections[0].content == "Summary text"
    assert sections[4].title == "Risk Score"


def test_sections_to_markdown() -> None:
    patient = {"full_name": "Asha Rao", "age": 32, "risk_level": "Low"}
    sections = format_report('{"Patient Summary": "Summary text"}', patient)
    markdown = sections_to_markdown(sections)
    assert "## Patient Summary" in markdown
    assert "Summary text" in markdown

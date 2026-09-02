from assessment_engine import UNKNOWN_ANSWER, AssessmentQuestion, AssessmentSession, parse_next_question_decision


def test_session_starts_with_fixed_questions() -> None:
    session = AssessmentSession()
    assert session.current_question().question_id == "full_name"
    session.answer_current("Asha Rao")
    assert session.current_question().question_id == "age"


def test_session_needs_ai_after_primary_concern() -> None:
    session = AssessmentSession()
    for answer in ["Asha Rao", "32", "Female", "Fever for three days"]:
        session.answer_current(answer)
    assert session.needs_ai_decision()


def test_parse_continue_decision() -> None:
    raw = """
    {
      "status": "continue",
      "risk_hint": "Moderate",
      "question": {
        "id": "fever_duration",
        "text": "Since when do you have fever?",
        "input_type": "text",
        "clinical_reason": "Duration helps estimate severity."
      }
    }
    """
    decision = parse_next_question_decision(raw)
    assert decision.status == "continue"
    assert decision.risk_hint == "Moderate"
    assert decision.question.text == "Since when do you have fever?"


def test_parse_complete_decision() -> None:
    decision = parse_next_question_decision('{"status": "complete", "risk_hint": "Low"}')
    assert decision.status == "complete"
    assert decision.question is None


def test_unknown_answer_is_allowed_for_dynamic_questions() -> None:
    session = AssessmentSession()
    for answer in ["Asha Rao", "32", "Female", "Fever for three days"]:
        session.answer_current(answer)
    session.current_dynamic_question = AssessmentQuestion(
        "highest_temperature",
        "What is your highest temperature?",
        "number",
        clinical_reason="Temperature helps estimate fever severity.",
    )
    session.answer_current(UNKNOWN_ANSWER)
    assert session.answers[-1].answer == UNKNOWN_ANSWER

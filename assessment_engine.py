"""Adaptive clinical assessment state machine."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class AssessmentQuestion:
    """One clinical intake question shown to the patient."""

    question_id: str
    text: str
    input_type: str = "text"
    options: tuple[str, ...] = ()
    clinical_reason: str = ""


@dataclass(frozen=True)
class AnswerRecord:
    """A single remembered patient answer."""

    question_id: str
    question: str
    answer: str
    clinical_reason: str = ""
    source: str = "engine"


@dataclass(frozen=True)
class NextQuestionDecision:
    """Gemini decision for the next assessment step."""

    status: str
    question: AssessmentQuestion | None = None
    completion_reason: str = ""
    risk_hint: str = "Under review"


INITIAL_QUESTIONS = (
    AssessmentQuestion("full_name", "What is the patient's full name?", "text", clinical_reason="Patient identity"),
    AssessmentQuestion("age", "What is the patient's age?", "number", clinical_reason="Age changes clinical risk"),
    AssessmentQuestion(
        "gender",
        "What is the patient's gender?",
        "choice",
        ("Female", "Male", "Non-binary", "Prefer not to say"),
        "Basic demographic context",
    ),
    AssessmentQuestion(
        "primary_concern",
        "What is the primary health concern today?",
        "textarea",
        clinical_reason="Main presenting complaint",
    ),
)

UNKNOWN_ANSWER = "I don't know / Not sure"


@dataclass
class AssessmentSession:
    """Stateful adaptive interview engine for one assessment."""

    answers: list[AnswerRecord] = field(default_factory=list)
    current_dynamic_question: AssessmentQuestion | None = None
    completed: bool = False
    completion_reason: str = ""
    risk_hint: str = "Under review"
    max_dynamic_questions: int = 9

    def reset(self) -> None:
        """Reset assessment memory."""
        self.answers.clear()
        self.current_dynamic_question = None
        self.completed = False
        self.completion_reason = ""
        self.risk_hint = "Under review"

    @property
    def fixed_answer_count(self) -> int:
        """Return how many fixed opening questions have been answered."""
        answered_ids = {answer.question_id for answer in self.answers}
        return sum(1 for question in INITIAL_QUESTIONS if question.question_id in answered_ids)

    @property
    def dynamic_answer_count(self) -> int:
        """Return how many Gemini-driven follow-up questions have been answered."""
        fixed_ids = {question.question_id for question in INITIAL_QUESTIONS}
        return sum(1 for answer in self.answers if answer.question_id not in fixed_ids)

    def current_question(self) -> AssessmentQuestion | None:
        """Return the current question to render."""
        if self.completed:
            return None
        if self.fixed_answer_count < len(INITIAL_QUESTIONS):
            return INITIAL_QUESTIONS[self.fixed_answer_count]
        return self.current_dynamic_question

    def progress_percent(self) -> int:
        """Estimate progress without pretending the adaptive interview has a fixed length."""
        if self.completed:
            return 100
        answered = len(self.answers)
        return min(92, 12 + answered * 8)

    def answer_current(self, raw_answer: object) -> None:
        """Validate and store the answer for the current question."""
        question = self.current_question()
        if question is None:
            raise ValueError("There is no active question.")

        answer = normalize_answer(raw_answer)
        validate_answer(question, answer)
        source = "intake" if self.fixed_answer_count < len(INITIAL_QUESTIONS) else "gemini"
        self.answers.append(
            AnswerRecord(
                question_id=question.question_id,
                question=question.text,
                answer=answer,
                clinical_reason=question.clinical_reason,
                source=source,
            )
        )
        if source == "gemini":
            self.current_dynamic_question = None

    def needs_ai_decision(self) -> bool:
        """Return whether Gemini should decide the next step."""
        return (
            not self.completed
            and self.fixed_answer_count == len(INITIAL_QUESTIONS)
            and self.current_dynamic_question is None
        )

    def apply_decision(self, decision: NextQuestionDecision) -> None:
        """Apply a Gemini next-question or completion decision."""
        self.risk_hint = decision.risk_hint or self.risk_hint
        if decision.status == "complete" or self.dynamic_answer_count >= self.max_dynamic_questions:
            self.completed = True
            self.current_dynamic_question = None
            self.completion_reason = decision.completion_reason or "Sufficient clinical context has been collected."
            return
        if decision.question is None:
            raise ValueError("A continue decision must include one question.")
        self.current_dynamic_question = decision.question

    def context(self) -> dict[str, object]:
        """Return structured assessment memory for prompts and reports."""
        return {
            "patient": self.patient_summary(),
            "answers": [answer.__dict__ for answer in self.answers],
            "risk_hint": self.risk_hint,
            "completion_reason": self.completion_reason,
            "dynamic_answer_count": self.dynamic_answer_count,
        }

    def patient_summary(self) -> dict[str, object]:
        """Return patient details inferred from the assessment answers."""
        lookup = {answer.question_id: answer.answer for answer in self.answers}
        return {
            "full_name": lookup.get("full_name", "Patient"),
            "age": lookup.get("age", "Not specified"),
            "gender": lookup.get("gender", "Not specified"),
            "primary_concern": lookup.get("primary_concern", "Not specified"),
            "risk_level": self.risk_hint,
            "answered_questions": len(self.answers),
        }


def normalize_answer(raw_answer: object) -> str:
    """Convert a UI value into a clean answer string."""
    return "" if raw_answer is None else str(raw_answer).strip()


def validate_answer(question: AssessmentQuestion, answer: str) -> None:
    """Validate a single assessment answer."""
    if answer == UNKNOWN_ANSWER and should_offer_unknown(question):
        return
    if not answer:
        raise ValueError("Please answer the current question before continuing.")
    if question.input_type == "number":
        try:
            number = int(float(answer))
        except ValueError as exc:
            raise ValueError("Please enter a valid number.") from exc
        if question.question_id == "age" and not 1 <= number <= 120:
            raise ValueError("Age must be between 1 and 120.")
    if question.question_id == "primary_concern" and len(answer) < 3:
        raise ValueError("Please describe the health concern a little more clearly.")
    if question.options and answer not in question.options:
        raise ValueError("Please choose one of the available options.")


def should_offer_unknown(question: AssessmentQuestion) -> bool:
    """Return whether a patient can safely continue without knowing the answer."""
    required_opening_ids = {"full_name", "age", "gender", "primary_concern"}
    return question.question_id not in required_opening_ids


def parse_next_question_decision(raw_text: str) -> NextQuestionDecision:
    """Parse Gemini JSON into a safe next-question decision."""
    data = _extract_json(raw_text)
    status = str(data.get("status", "continue")).strip().lower()
    if status not in {"continue", "complete"}:
        status = "continue"

    risk_hint = str(data.get("risk_hint", "Under review")).strip() or "Under review"
    completion_reason = str(data.get("completion_reason", "")).strip()
    question_data = data.get("question") if isinstance(data.get("question"), dict) else {}

    question = None
    if status == "continue":
        text = str(question_data.get("text", "")).strip()
        if not text:
            text = "What symptom or change should be assessed next?"
        input_type = str(question_data.get("input_type", "text")).strip().lower()
        if input_type not in {"text", "textarea", "number", "choice", "yes_no"}:
            input_type = "text"
        raw_options = question_data.get("options", [])
        options = tuple(str(option).strip() for option in raw_options if str(option).strip())[:5]
        if input_type == "yes_no":
            options = ("Yes", "No", UNKNOWN_ANSWER)
        elif input_type == "choice" and UNKNOWN_ANSWER not in options:
            options = (*options, UNKNOWN_ANSWER)
        question = AssessmentQuestion(
            question_id=str(question_data.get("id", f"followup_{abs(hash(text))}")).strip(),
            text=text,
            input_type=input_type,
            options=options,
            clinical_reason=str(question_data.get("clinical_reason", "")).strip(),
        )

    return NextQuestionDecision(
        status=status,
        question=question,
        completion_reason=completion_reason,
        risk_hint=risk_hint,
    )


def _extract_json(raw_text: str) -> dict[str, object]:
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
        raise ValueError("Assessment decision must be a JSON object.")
    return parsed

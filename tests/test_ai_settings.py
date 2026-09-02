import asyncio

import app
from assessment_engine import AssessmentSession
from health_ai import GeminiModelInfo, HealthAiError


def test_model_selection_normalizes_display_name_to_model_id() -> None:
    storage: dict[str, object] = {}
    settings = app.ai_settings(storage)
    settings.update(
        {
            "validated": True,
            "available_models": [
                {
                    "name": "models/gemini-test",
                    "display_name": "Gemini Test",
                    "description": "",
                    "supported_actions": ["generateContent"],
                }
            ],
            "selected_model": "",
        }
    )

    app._configure_model_selection("Gemini Test", storage)

    assert app.ai_ready(storage)
    assert app._generation_settings(storage).model_name == "models/gemini-test"
    assert "api_key" not in app.ai_settings(storage)


def test_ai_initialization_reuses_cached_models(monkeypatch) -> None:
    calls = 0

    class FakeGeminiClient:
        def __init__(self, api_key: str) -> None:
            self.api_key = api_key

        def list_text_models(self) -> list[GeminiModelInfo]:
            nonlocal calls
            calls += 1
            return [
                GeminiModelInfo(
                    name="models/gemini-2.5-flash",
                    display_name="Gemini 2.5 Flash",
                    description="Fast model",
                    supported_actions=("generateContent",),
                )
            ]

    storage: dict[str, object] = {}
    monkeypatch.setattr(app, "_APP_GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(app, "_APP_GEMINI_CLIENT", None)
    monkeypatch.setattr(app, "GeminiHealthClient", FakeGeminiClient)

    asyncio.run(app.ensure_ai_initialized(storage))
    asyncio.run(app.ensure_ai_initialized(storage))

    assert calls == 1
    assert app.ai_ready(storage)
    assert app.ai_settings(storage)["selected_model"] == "models/gemini-2.5-flash"


def test_ai_initialization_keeps_previous_cached_models_on_refresh_failure(monkeypatch) -> None:
    class FailingGeminiClient:
        def __init__(self, api_key: str) -> None:
            self.api_key = api_key

        def list_text_models(self) -> list[GeminiModelInfo]:
            raise HealthAiError("temporary model loading failure")

    storage: dict[str, object] = {}
    settings = app.ai_settings(storage)
    settings.update(
        {
            "validated": False,
            "status": "loading",
            "available_models": [
                {
                    "name": "models/gemini-cached",
                    "display_name": "Gemini Cached",
                    "description": "",
                    "supported_actions": ["generateContent"],
                }
            ],
            "selected_model": "models/gemini-cached",
        }
    )

    monkeypatch.setattr(app, "_APP_GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(app, "_APP_GEMINI_CLIENT", None)
    monkeypatch.setattr(app, "GeminiHealthClient", FailingGeminiClient)

    asyncio.run(app.ensure_ai_initialized(storage))

    refreshed = app.ai_settings(storage)
    assert refreshed["status"] == "connected"
    assert refreshed["validated"] is True
    assert refreshed["selected_model"] == "models/gemini-cached"
    assert len(refreshed["available_models"]) == 1


def test_gemini_client_is_created_once_and_reused(monkeypatch) -> None:
    created = 0

    class FakeGeminiClient:
        def __init__(self, api_key: str) -> None:
            nonlocal created
            created += 1
            self.api_key = api_key

    monkeypatch.setattr(app, "_APP_GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(app, "_APP_GEMINI_CLIENT", None)
    monkeypatch.setattr(app, "GeminiHealthClient", FakeGeminiClient)

    first = app._gemini_client()
    second = app._gemini_client()

    assert first is second
    assert created == 1


def test_dynamic_question_generation_uses_the_existing_assessment_pipeline(monkeypatch) -> None:
    class FakeGeminiClient:
        def generate_report(self, prompt: str, settings: object) -> str:
            assert "adaptive clinical assessment" in prompt
            return '''{
                "status": "continue",
                "risk_hint": "Moderate",
                "question": {
                    "id": "fever_duration",
                    "text": "Since when do you have fever?",
                    "input_type": "text",
                    "clinical_reason": "Duration helps assess the illness."
                }
            }'''

    session = AssessmentSession()
    for answer in ["Asha Rao", "32", "Female", "Fever for three days"]:
        session.answer_current(answer)

    monkeypatch.setattr(app.state, "session", session)
    monkeypatch.setattr(app.state, "processing", False)
    monkeypatch.setattr(app, "_active_ai_context", lambda storage=None: (FakeGeminiClient(), object()))

    assert asyncio.run(app.generate_next_question(reload_after=False)) is True
    assert app.state.session.current_question().question_id == "fever_duration"

# Redeploy trigger: Pick up new environment variables
"""Health Companion adaptive clinical assessment application."""

from __future__ import annotations

import asyncio
import os
from typing import Any

from nicegui import app as nicegui_app, ui

from assessment_engine import (
    UNKNOWN_ANSWER,
    AssessmentQuestion,
    AssessmentSession,
    parse_next_question_decision,
    should_offer_unknown,
)
from components import card, editorial_header, flat_card, metric, primary_button, secondary_button, sidebar
from config import (
    AI_OUTPUT_TOKEN_OPTIONS,
    AI_RESPONSE_STYLE_OPTIONS,
    DEFAULT_AI_MAX_OUTPUT_TOKENS,
    DEFAULT_AI_RESPONSE_STYLE,
    DEFAULT_AI_TEMPERATURE,
    get_gemini_api_key,
)
from health_ai import GeminiGenerationSettings, GeminiHealthClient, GeminiModelInfo, HealthAiError
from prompt_builder import build_final_assessment_prompt, build_next_question_prompt
from report_formatter import ReportSection, format_report, sections_to_markdown
from styles import apply_global_styles
from utils import export_report


class AppState:
    """In-memory state for a single local development session."""

    def __init__(self) -> None:
        self.session = AssessmentSession()
        self.report_sections: list[ReportSection] = []
        self.processing: bool = False
        self.assessment_error: str = ""


state = AppState()
apply_global_styles()


AI_SETTINGS_STORAGE_KEY = "hc_ai_settings"
MODEL_DISCOVERY_TIMEOUT_SECONDS = 15
_APP_GEMINI_API_KEY = get_gemini_api_key()
_APP_GEMINI_CLIENT: GeminiHealthClient | None = None
_ACTIVE_CLIENT = None
_AI_SETTINGS_STORE: dict[str, Any] = {}
_AI_INITIALIZATION_LOCK = asyncio.Lock()
_AI_INITIALIZATION_TASK: asyncio.Task[None] | None = None


def set_active_client() -> None:
    """Remember the current NiceGUI client for session-scoped async handlers."""
    global _ACTIVE_CLIENT
    _ACTIVE_CLIENT = ui.context.client


def default_ai_settings() -> dict[str, Any]:
    """Return a fresh default AI settings dictionary for the current session."""
    has_api_key = bool(_APP_GEMINI_API_KEY)
    return {
        "selected_model": "",
        "temperature": DEFAULT_AI_TEMPERATURE,
        "max_output_tokens": DEFAULT_AI_MAX_OUTPUT_TOKENS,
        "response_style": DEFAULT_AI_RESPONSE_STYLE,
        "validated": False,
        "status": "loading" if has_api_key else "missing",
        "status_message": "Loading Gemini settings from .env..." if has_api_key else "GEMINI_API_KEY was not found in .env.",
        "available_models": [],
        "connection_time_ms": None,
        "connection_details": "",
    }


def session_storage(storage: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return app-level AI settings storage for local development."""
    if storage is not None:
        return storage
    return _AI_SETTINGS_STORE


def ai_settings(storage: dict[str, Any] | None = None) -> dict[str, Any]:
    """Read or initialize the session-scoped AI settings."""
    storage = session_storage(storage)
    settings = storage.get(AI_SETTINGS_STORAGE_KEY)
    if not isinstance(settings, dict):
        settings = default_ai_settings()
        storage[AI_SETTINGS_STORAGE_KEY] = settings
        return settings

    defaults = default_ai_settings()
    for key, value in defaults.items():
        settings.setdefault(key, value)
    return settings


def update_ai_settings(storage: dict[str, Any] | None = None, **updates: Any) -> dict[str, Any]:
    """Persist changes to the current session AI settings."""
    settings = ai_settings(storage)
    settings.update(updates)
    session_storage(storage)[AI_SETTINGS_STORAGE_KEY] = settings
    return settings


def _model_dict_to_info(model: dict[str, Any]) -> GeminiModelInfo:
    return GeminiModelInfo(
        name=str(model.get("name", "") or "").strip(),
        display_name=str(model.get("display_name", "") or "").strip(),
        description=str(model.get("description", "") or "").strip(),
        output_token_limit=model.get("output_token_limit"),
        max_temperature=model.get("max_temperature"),
        supported_actions=tuple(str(item) for item in model.get("supported_actions", []) if str(item).strip()),
    )


def _model_info_to_dict(model: GeminiModelInfo) -> dict[str, Any]:
    return {
        "name": model.name,
        "display_name": model.display_name,
        "description": model.description,
        "output_token_limit": model.output_token_limit,
        "max_temperature": model.max_temperature,
        "supported_actions": list(model.supported_actions),
    }


def _available_model_options(storage: dict[str, Any] | None = None) -> list[GeminiModelInfo]:
    return [_model_dict_to_info(item) for item in ai_settings(storage).get("available_models", []) if isinstance(item, dict)]


def _selected_model_info(storage: dict[str, Any] | None = None) -> GeminiModelInfo | None:
    selected_model = str(ai_settings(storage).get("selected_model", "") or "").strip()
    if not selected_model:
        return None
    for model in _available_model_options(storage):
        if model.name == selected_model:
            return model
    return None


def _generation_settings(storage: dict[str, Any] | None = None) -> GeminiGenerationSettings | None:
    settings = ai_settings(storage)
    selected_model = _selected_model_info(storage)
    if not _APP_GEMINI_API_KEY or selected_model is None:
        return None
    return GeminiGenerationSettings(
        model_name=selected_model.name,
        temperature=float(settings.get("temperature", DEFAULT_AI_TEMPERATURE) or DEFAULT_AI_TEMPERATURE),
        max_output_tokens=int(settings.get("max_output_tokens", DEFAULT_AI_MAX_OUTPUT_TOKENS) or DEFAULT_AI_MAX_OUTPUT_TOKENS),
        response_style=str(settings.get("response_style", DEFAULT_AI_RESPONSE_STYLE) or DEFAULT_AI_RESPONSE_STYLE),
    )


def _gemini_client(storage: dict[str, Any] | None = None) -> GeminiHealthClient | None:
    """Return the single Gemini client shared by the local application."""
    global _APP_GEMINI_CLIENT
    if not _APP_GEMINI_API_KEY:
        return None
    if _APP_GEMINI_CLIENT is None:
        _APP_GEMINI_CLIENT = GeminiHealthClient(_APP_GEMINI_API_KEY)
    return _APP_GEMINI_CLIENT


def ai_ready(storage: dict[str, Any] | None = None) -> bool:
    """Return whether the session has a validated Gemini key and model selection."""
    settings = ai_settings(storage)
    return bool(
        settings.get("validated")
        and _APP_GEMINI_API_KEY
        and _selected_model_info(storage) is not None
    )


def _selected_model_label(storage: dict[str, Any] | None = None) -> str:
    model = _selected_model_info(storage)
    if model is None:
        return "Not selected"
    return model.display_name or model.name


def _model_summary(model: GeminiModelInfo | None) -> dict[str, str]:
    if model is None:
        return {
            "best_use_case": "Validate a Gemini API key to load models.",
            "speed": "Ready after connection",
            "quality": "Choose a model to view quality guidance.",
            "recommendation": "Model selection required.",
        }

    display_name = model.display_name or model.name
    searchable = f"{model.name} {model.display_name} {model.description}".lower()
    if "flash" in searchable:
        return {
            "best_use_case": "Fast response for the clinical interview and report drafting.",
            "speed": "Fast",
            "quality": "Balanced",
            "recommendation": f"{display_name} is recommended for Health Companion.",
        }
    if "pro" in searchable:
        return {
            "best_use_case": "Deeper reasoning and more nuanced clinical output.",
            "speed": "Moderate",
            "quality": "Highest",
            "recommendation": f"{display_name} is recommended when depth matters more than speed.",
        }
    return {
        "best_use_case": model.description or "General text generation for the health workflow.",
        "speed": "Moderate",
        "quality": "Balanced",
        "recommendation": f"{display_name} is suitable for Health Companion.",
    }


def _first_working_model(client: GeminiHealthClient, models: list[GeminiModelInfo]) -> GeminiModelInfo:
    """Return the first detected model that can complete a tiny request."""
    for model in models:
        settings = GeminiGenerationSettings(
            model_name=model.name,
            temperature=0.0,
            max_output_tokens=64,
            response_style=DEFAULT_AI_RESPONSE_STYLE,
        )
        result = client.test_connection(settings)
        if result.success:
            return model
    raise HealthAiError("No detected Gemini text model completed the connection test. Please try another API key or project.")


def _preferred_model(models: list[GeminiModelInfo]) -> GeminiModelInfo:
    """Prefer Gemini 2.5 Flash when available, otherwise use the first working model."""
    for model in models:
        if "gemini-2.5-flash" in model.name.lower():
            return model
    return models[0]


async def ensure_ai_initialized(storage: dict[str, Any] | None = None) -> None:
    """Silently load and validate Gemini configuration from .env once."""
    storage = session_storage(storage)
    settings = ai_settings(storage)
    if settings.get("validated") and _selected_model_info(storage) is not None:
        return
    if settings.get("status") == "validating":
        return

    if not _APP_GEMINI_API_KEY:
        update_ai_settings(
            storage=storage,
            validated=False,
            status="missing",
            status_message="GEMINI_API_KEY was not found in .env.",
            available_models=[],
            selected_model="",
        )
        return

    async with _AI_INITIALIZATION_LOCK:
        settings = ai_settings(storage)
        if settings.get("validated") and _selected_model_info(storage) is not None:
            return

        previous_model_dicts = [
            item for item in settings.get("available_models", []) if isinstance(item, dict)
        ]
        previous_models = [_model_dict_to_info(item) for item in previous_model_dicts]
        previous_selected = str(settings.get("selected_model", "") or "").strip()
        if previous_models and not previous_selected:
            previous_selected = _preferred_model(previous_models).name

        update_ai_settings(
            storage=storage,
            validated=bool(previous_models and previous_selected),
            status="validating",
            status_message="Validating Gemini from .env...",
            available_models=previous_model_dicts,
            selected_model=previous_selected,
        )

        try:
            client = _gemini_client(storage)
            if client is None:
                raise HealthAiError("GEMINI_API_KEY was not found in .env.")
            models = await asyncio.wait_for(
                asyncio.to_thread(client.list_text_models),
                timeout=MODEL_DISCOVERY_TIMEOUT_SECONDS,
            )
            if not models:
                raise HealthAiError("No compatible Gemini text-generation models were found.")

            selected_model = _preferred_model(models)
            model_dicts = [_model_info_to_dict(model) for model in models]
            update_ai_settings(
                storage=storage,
                validated=True,
                status="connected",
                status_message="Gemini Connected",
                selected_model=selected_model.name,
                available_models=model_dicts,
                connection_details=f"{len(model_dicts)} compatible models available.",
            )
        except asyncio.TimeoutError:
            failure_message = "Gemini model discovery timed out. Please restart the local app and try again."
            has_cached_models = bool(previous_model_dicts and previous_selected)
            update_ai_settings(
                storage=storage,
                validated=has_cached_models,
                status="connected" if has_cached_models else "error",
                status_message="Gemini Connected" if has_cached_models else failure_message,
                available_models=previous_model_dicts,
                selected_model=previous_selected,
                connection_details=(
                    f"Using cached model list. Latest refresh timed out after {MODEL_DISCOVERY_TIMEOUT_SECONDS} seconds."
                    if has_cached_models
                    else failure_message
                ),
            )
        except HealthAiError as exc:
            has_cached_models = bool(previous_model_dicts and previous_selected)
            update_ai_settings(
                storage=storage,
                validated=has_cached_models,
                status="connected" if has_cached_models else "error",
                status_message="Gemini Connected" if has_cached_models else str(exc),
                available_models=previous_model_dicts,
                selected_model=previous_selected,
                connection_details=(
                    f"Using cached model list. Latest refresh failed: {exc}"
                    if has_cached_models
                    else str(exc)
                ),
            )


def start_ai_initialization() -> None:
    """Start the one-time Gemini initialization without blocking the UI."""
    global _AI_INITIALIZATION_TASK
    if _AI_INITIALIZATION_TASK is not None and not _AI_INITIALIZATION_TASK.done():
        return
    if ai_ready(_AI_SETTINGS_STORE):
        return
    _AI_INITIALIZATION_TASK = asyncio.create_task(ensure_ai_initialized(_AI_SETTINGS_STORE))


async def initialize_ai_on_startup() -> None:
    """Kick off Gemini initialization once when the local app starts."""
    start_ai_initialization()


nicegui_app.on_startup(initialize_ai_on_startup)


def _status_style(status: str) -> tuple[str, str, str]:
    normalized = status.lower().strip()
    if normalized == "connected":
        return "check_circle", "Connected Successfully", "hc-status-chip hc-status-success"
    if normalized == "validating":
        return "hourglass_top", "Validating...", "hc-status-chip hc-status-warning"
    if normalized in {"invalid", "network", "error"}:
        label = {
            "invalid": "Invalid API Key",
            "network": "Network Error",
            "error": "Connection Failed",
        }[normalized]
        return "error", label, "hc-status-chip hc-status-danger"
    if normalized == "ready":
        return "verified", "Ready", "hc-status-chip hc-status-success"
    if normalized == "loading":
        return "hourglass_top", "Loading...", "hc-status-chip hc-status-warning"
    return "radio_button_unchecked", "Not Configured", "hc-status-chip hc-status-warning"


def _sync_ui_settings_state(model_select: Any | None = None, storage: dict[str, Any] | None = None) -> None:
    """Refresh visible settings controls from session storage."""
    settings = ai_settings(storage)
    if model_select is not None:
        model_select.options = {model.name: model.display_name or model.name for model in _available_model_options(storage)}
        selected_model = _selected_model_info(storage)
        model_select.value = selected_model.name if selected_model else None
        if settings.get("validated") and settings.get("available_models"):
            model_select.enable()
        else:
            model_select.disable()


def _configure_model_selection(selected_model: str | None, storage: dict[str, Any] | None = None) -> None:
    selected_value = str(selected_model or "").strip()
    if not selected_value:
        return
    for model in _available_model_options(storage):
        if selected_value in {model.name, model.display_name}:
            update_ai_settings(storage=storage, selected_model=model.name)
            return
    update_ai_settings(storage=storage, selected_model=selected_value)


def _requires_ai_configuration() -> bool:
    return not ai_ready()


def _active_ai_context(storage: dict[str, Any] | None = None) -> tuple[GeminiHealthClient, GeminiGenerationSettings] | None:
    client = _gemini_client(storage)
    settings = _generation_settings(storage)
    if client is None or settings is None:
        return None
    return client, settings


def notify(message: str, kind: str = "info") -> None:
    """Show a consistent professional notification."""
    colors = {"positive": "positive", "negative": "negative", "warning": "warning", "info": "info"}
    try:
        ui.notify(message, type=colors.get(kind, "info"), position="top-right", close_button=True)
    except RuntimeError:
        return


@ui.page("/")
def landing_page() -> None:
    """Open the assessment directly."""
    ui.navigate.to("/patient" if ai_ready() else "/connect")


@ui.page("/setup")
def setup_page() -> None:
    """Retained as a redirect for old links."""
    ui.navigate.to("/connect")


@ui.page("/connect")
@ui.page("/ai-settings")
def simplified_ai_settings_page() -> None:
    """Render simplified AI settings loaded automatically from .env."""
    set_active_client()
    session_store = session_storage()
    sidebar("AI Settings")
    settings = ai_settings(session_store)

    with ui.column().classes("hc-shell ml-0 md:ml-72 px-6 py-10 gap-8"):
        editorial_header(
            "AI settings",
            "Gemini is loaded automatically from .env. Choose the model and response settings for your local assessment workflow.",
        )

        with ui.row().classes("gap-4 flex-wrap"):
            with flat_card("min-w-64"):
                ui.label("Status").classes("text-xs uppercase tracking-widest hc-muted")
                status_label = ui.label("Loading Gemini").classes("hc-serif text-3xl mt-1")
                status_detail = ui.label("Reading GEMINI_API_KEY from .env.").classes("text-xs hc-muted mt-1")
            with flat_card("min-w-64"):
                ui.label("Current Model").classes("text-xs uppercase tracking-widest hc-muted")
                current_model_label = ui.label("Loading").classes("hc-serif text-3xl mt-1")
                current_model_detail = ui.label("Auto-selecting Gemini 2.5 Flash when available.").classes("text-xs hc-muted mt-1")
            with flat_card("min-w-64"):
                ui.label("Available Models").classes("text-xs uppercase tracking-widest hc-muted")
                available_models_label = ui.label("0").classes("hc-serif text-3xl mt-1")
                ui.label("Compatible Gemini text models.").classes("text-xs hc-muted mt-1")

        with card("w-full max-w-4xl hc-setting-card hc-fade-in"):
            ui.label("Model and response settings").classes("text-xs uppercase tracking-widest hc-muted")
            ui.label("The API key is never shown in the interface. It is read silently from the local .env file.").classes(
                "hc-muted leading-6 mt-2"
            )

            model_select = ui.select({}, label="AI Model").props("outlined emit-value map-options").classes("w-full mt-5")
            model_select.disable()

            with ui.card().classes("hc-card-flat mt-5 p-4"):
                model_info_title = ui.label("Loading model details").classes("hc-serif text-2xl")
                model_info_use_case = ui.label("Model details appear after Gemini connects.").classes("hc-muted leading-6 mt-2")
                with ui.row().classes("gap-2 mt-4 flex-wrap"):
                    model_info_speed = ui.label("Speed: --").classes("hc-status-chip hc-status-warning")
                    model_info_quality = ui.label("Quality: --").classes("hc-status-chip hc-status-warning")
                    model_info_recommendation = ui.label("Recommendation: --").classes("hc-status-chip hc-status-warning")

            with ui.card().classes("hc-card-flat mt-5 p-4"):
                ui.label("AI configuration").classes("text-xs uppercase tracking-widest hc-muted")
                temperature_label = ui.label(f"Temperature: {float(settings.get('temperature', DEFAULT_AI_TEMPERATURE)):0.1f}").classes(
                    "hc-serif text-2xl mt-2"
                )
                temperature_slider = ui.slider(
                    min=0.0,
                    max=1.0,
                    step=0.05,
                    value=float(settings.get("temperature", DEFAULT_AI_TEMPERATURE)),
                ).classes("w-full mt-3")
                temperature_slider.props("label always-show")

                ui.label("Maximum output tokens").classes("text-xs uppercase tracking-widest hc-muted mt-5")
                token_select = ui.select(
                    [str(token) for token in AI_OUTPUT_TOKEN_OPTIONS],
                    value=str(settings.get("max_output_tokens", DEFAULT_AI_MAX_OUTPUT_TOKENS)),
                ).props("outlined").classes("w-full mt-2")

                ui.label("Response style").classes("text-xs uppercase tracking-widest hc-muted mt-5")
                style_select = ui.select(
                    list(AI_RESPONSE_STYLE_OPTIONS),
                    value=str(settings.get("response_style", DEFAULT_AI_RESPONSE_STYLE)),
                ).props("outlined").classes("w-full mt-2")

        def update_model_preview() -> None:
            selected = _selected_model_info(session_store)
            summary = _model_summary(selected)
            if selected is None:
                model_info_title.text = "No model selected"
                model_info_use_case.text = "Gemini model details will appear after connection."
                model_info_speed.text = "Speed: --"
                model_info_quality.text = "Quality: --"
                model_info_recommendation.text = "Recommendation: --"
                current_model_label.text = "Not Ready"
                current_model_detail.text = "Waiting for Gemini connection."
                return

            model_info_title.text = selected.display_name or selected.name
            model_info_use_case.text = summary["best_use_case"]
            model_info_speed.text = f"Speed: {summary['speed']}"
            model_info_quality.text = f"Quality: {summary['quality']}"
            model_info_recommendation.text = summary["recommendation"]
            current_model_label.text = selected.display_name or selected.name
            current_model_detail.text = selected.name

        def refresh_settings_ui() -> None:
            settings_now = ai_settings(session_store)
            models = _available_model_options(session_store)
            status = str(settings_now.get("status", "missing"))
            model_select.options = {model.name: model.display_name or model.name for model in models}
            selected = _selected_model_info(session_store)
            model_select.value = selected.name if selected else None
            model_select.enable() if models else model_select.disable()
            available_models_label.text = str(len(models))

            if status == "connected":
                status_label.text = "Gemini Connected"
                status_detail.text = str(settings_now.get("connection_details") or "Loaded from .env and ready for assessment.")
            elif status == "validating":
                status_label.text = "Validating Gemini"
                status_detail.text = "Checking .env configuration in the background."
            elif status == "loading":
                status_label.text = "Loading Gemini"
                status_detail.text = "Startup initialization is running in the background."
            elif status == "missing":
                status_label.text = "Gemini Not Configured"
                status_detail.text = "Add GEMINI_API_KEY to .env and restart the app."
            else:
                status_label.text = "Gemini Error"
                status_detail.text = str(settings_now.get("status_message", "Could not initialize Gemini."))

            update_model_preview()

        def on_model_change(event: Any) -> None:
            _configure_model_selection(str(getattr(event, "value", "") or ""), session_store)
            refresh_settings_ui()

        def update_temperature(event: Any) -> None:
            temperature_value = float(getattr(event, "value", DEFAULT_AI_TEMPERATURE))
            temperature_label.text = f"Temperature: {temperature_value:0.1f}"
            update_ai_settings(storage=session_store, temperature=temperature_value)

        def update_tokens(event: Any) -> None:
            token_value = int(float(str(getattr(event, "value", DEFAULT_AI_MAX_OUTPUT_TOKENS))))
            update_ai_settings(storage=session_store, max_output_tokens=token_value)

        def update_response_style(event: Any) -> None:
            update_ai_settings(storage=session_store, response_style=str(getattr(event, "value", DEFAULT_AI_RESPONSE_STYLE)))

        model_select.on("update:model-value", on_model_change)
        temperature_slider.on("update:model-value", update_temperature)
        token_select.on("update:model-value", update_tokens)
        style_select.on("update:model-value", update_response_style)

        refresh_settings_ui()
        ui.timer(1.0, refresh_settings_ui)


@ui.page("/patient")
def assessment_page() -> None:
    """Render the adaptive assessment workspace."""
    set_active_client()
    sidebar("Adaptive Assessment")
    with ui.column().classes("hc-shell ml-0 md:ml-72 px-6 py-10 gap-8"):
        editorial_header(
            "Adaptive assessment",
            "Answer one clinical question at a time. The next question is selected from the assessment memory, like a structured physician interview.",
        )

        if _requires_ai_configuration():
            settings_now = ai_settings()
            with card("w-full max-w-3xl"):
                if str(settings_now.get("status")) == "error":
                    ui.icon("error_outline").classes("text-3xl text-red-700")
                    ui.label("Gemini could not initialize").classes("hc-serif text-3xl mt-2")
                    ui.label(str(settings_now.get("status_message", "Check your .env configuration."))).classes(
                        "hc-muted leading-6 mt-2"
                    )
                    with ui.row().classes("gap-3 mt-5"):
                        primary_button("Open AI Settings", on_click=lambda: ui.navigate.to("/connect"), icon="tune")
                elif not _APP_GEMINI_API_KEY:
                    ui.icon("settings").classes("text-3xl hc-accent")
                    ui.label("Gemini key missing").classes("hc-serif text-3xl mt-2")
                    ui.label("Add GEMINI_API_KEY to .env and restart the app.").classes("hc-muted leading-6 mt-2")
                else:
                    ui.spinner(size="lg").classes("hc-accent")
                    ui.label("Gemini is initializing").classes("hc-serif text-3xl mt-4")
                    ui.label("Model loading is running in the background. This page is not calling Gemini directly.").classes("hc-muted mt-2")
                    with ui.row().classes("gap-3 mt-5"):
                        primary_button("Open AI Settings", on_click=lambda: ui.navigate.to("/connect"), icon="tune")
            return

        session = state.session
        with ui.row().classes("gap-4 flex-wrap"):
            metric("Progress", f"{session.progress_percent()}%", "Adaptive estimate")
            metric("Answered", str(len(session.answers)), "Clinical memory")
            metric("Risk", session.risk_hint, "Updated by Gemini")

        ui.linear_progress(value=session.progress_percent() / 100).classes("w-full max-w-5xl")

        if session.completed:
            render_completion_card()
            render_assessment_memory()
            return

        question = session.current_question()
        if question is None and session.needs_ai_decision():
            render_next_question_state()
            return

        if question is None:
            render_completion_card()
            return

        render_question_card(question)
        render_assessment_memory()


def render_question_card(question: AssessmentQuestion) -> None:
    """Render the current adaptive assessment question."""
    with card("w-full max-w-4xl p-8"):
        ui.label("Current clinical question").classes("text-xs uppercase tracking-widest hc-muted")
        ui.label(question.text).classes("hc-serif text-4xl leading-tight mt-3")
        with flat_card("w-full mt-5"):
            ui.label("Why this matters").classes("text-xs uppercase tracking-widest hc-muted")
            ui.label(reasoning_for_question(question)).classes("hc-muted leading-6 mt-2")

        answer_widget = build_answer_widget(question)
        error_label = ui.label("").classes("text-sm text-red-700 mt-2")
        status_label = ui.label("").classes("text-sm hc-muted mt-3")

        async def submit_answer(answer_override: str | None = None) -> None:
            if state.processing:
                return
            active_question = state.session.current_question()
            if active_question is None:
                if state.session.needs_ai_decision():
                    await generate_next_question()
                else:
                    ui.navigate.reload()
                return

            continue_button.disable()
            continue_button.props("loading")
            unknown_button.disable() if unknown_button is not None else None
            status_label.text = "Saving answer..."
            try:
                state.session.answer_current(answer_override if answer_override is not None else answer_widget.value)
            except ValueError as exc:
                error_label.text = str(exc)
                notify(str(exc), "warning")
                continue_button.enable()
                continue_button.props(remove="loading")
                unknown_button.enable() if unknown_button is not None else None
                return

            error_label.text = ""
            if state.session.needs_ai_decision():
                status_label.text = "Preparing the next clinical question..."
                await generate_next_question(reload_after=False)
                ui.navigate.reload()
            else:
                ui.navigate.reload()

        async def continue_click() -> None:
            await submit_answer()

        async def submit_unknown() -> None:
            await submit_answer(UNKNOWN_ANSWER)

        with ui.row().classes("gap-3 mt-8"):
            continue_button = primary_button(
                "Continue Assessment",
                on_click=continue_click,
                icon="arrow_forward",
            )
            unknown_button = None
            if should_offer_unknown(question):
                unknown_button = secondary_button("I don't know", on_click=submit_unknown, icon="help_outline")
            secondary_button("Reset Assessment", on_click=reset_assessment, icon="restart_alt")


def build_answer_widget(question: AssessmentQuestion) -> Any:
    """Build the right input control for a question."""
    if question.input_type in {"choice", "yes_no"}:
        options = list(question.options or ("Yes", "No"))
        if should_offer_unknown(question) and UNKNOWN_ANSWER not in options:
            options.append(UNKNOWN_ANSWER)
        return ui.select(options, label="Select answer").props("outlined").classes("w-full mt-6")
    if question.input_type == "number":
        return ui.number("Answer").props("outlined").classes("w-full mt-6")
    if question.input_type == "textarea":
        return ui.textarea("Answer").props("outlined autogrow").classes("w-full mt-6")
    return ui.input("Answer").props("outlined").classes("w-full mt-6")


def reasoning_for_question(question: AssessmentQuestion) -> str:
    """Return a helpful patient-facing explanation for the current question."""
    if question.clinical_reason:
        base = question.clinical_reason.rstrip(".")
    else:
        base = "This answer helps the assessment engine choose the next clinically relevant follow-up"
    if should_offer_unknown(question):
        return f"{base}. If you are not sure, choose 'I don't know' and the assessment will continue with a simpler related question."
    return f"{base}. This opening detail is needed to build the assessment context."


def render_next_question_state() -> None:
    """Render loading or retry state while deciding the next question."""
    with card("w-full max-w-4xl"):
        if state.assessment_error:
            ui.icon("error_outline").classes("text-4xl text-red-700")
            ui.label("Next question could not be prepared").classes("hc-serif text-3xl mt-4")
            ui.label(state.assessment_error).classes("hc-muted leading-6 mt-2")
            with ui.row().classes("gap-3 mt-6"):
                primary_button("Try Again", on_click=retry_next_question, icon="refresh")
                secondary_button("Reset Assessment", on_click=reset_assessment, icon="restart_alt")
            return

        ui.spinner(size="lg").classes("hc-accent")
        ui.label("Preparing the next clinical question...").classes("hc-serif text-3xl mt-4")
        ui.label("The assessment engine is reviewing previous answers.").classes("hc-muted mt-2")
    request_next_question(ui.context.client)


async def retry_next_question() -> None:
    """Retry next-question generation after a recoverable error."""
    state.assessment_error = ""
    await generate_next_question(reload_after=True)


async def generate_next_question(reload_after: bool = True, browser_client: Any | None = None) -> bool:
    """Ask Gemini to decide the next clinical question."""
    if state.processing:
        return False
    active_context = _active_ai_context()
    if active_context is None:
        notify("Gemini is still loading from .env. Please wait a moment.", "warning")
        return False

    client, generation_settings = active_context
    state.processing = True
    state.assessment_error = ""
    notify("Reviewing assessment memory...", "info")
    try:
        prompt = build_next_question_prompt(state.session.context())
        raw_decision = await asyncio.to_thread(client.generate_report, prompt, generation_settings)
        decision = parse_next_question_decision(raw_decision)
        state.session.apply_decision(decision)
        if reload_after:
            if browser_client is not None:
                browser_client.run_javascript("history.go(0)")
            else:
                ui.navigate.reload()
        return True
    except (HealthAiError, ValueError) as exc:
        state.assessment_error = f"Could not prepare the next question. {exc}"
        notify(state.assessment_error, "negative")
        if reload_after:
            if browser_client is not None:
                browser_client.run_javascript("history.go(0)")
            else:
                ui.navigate.reload()
        return False
    finally:
        state.processing = False


def request_next_question(browser_client: Any) -> None:
    """Schedule the recovery path without attaching a timer to a disposable page slot."""
    if state.processing or not state.session.needs_ai_decision():
        return
    asyncio.create_task(generate_next_question(reload_after=True, browser_client=browser_client))


def render_completion_card() -> None:
    """Render completion state and report action."""
    with card("w-full max-w-4xl p-8"):
        ui.icon("task_alt").classes("text-4xl hc-accent")
        ui.label("Assessment ready for report").classes("hc-serif text-4xl mt-3")
        reason = state.session.completion_reason or "Sufficient clinical information has been collected."
        ui.label(reason).classes("hc-muted leading-6 mt-3")

        async def generate_report() -> None:
            active_context = _active_ai_context()
            if active_context is None:
                notify("Gemini is still loading from .env. Please wait a moment.", "warning")
                return
            client, generation_settings = active_context
            try:
                notify("Generating clinical report...", "info")
                prompt = build_final_assessment_prompt(state.session.context())
                raw_report = await asyncio.to_thread(client.generate_report, prompt, generation_settings)
                patient = state.session.patient_summary()
                state.report_sections = format_report(raw_report, patient)
                ui.navigate.to("/report")
            except HealthAiError as exc:
                notify(str(exc), "negative")

        with ui.row().classes("gap-3 mt-8"):
            primary_button("Generate Clinical Report", on_click=generate_report, icon="article")
            secondary_button("Ask Another Assessment", on_click=reset_assessment, icon="restart_alt")


def render_assessment_memory() -> None:
    """Render structured assessment memory without chat styling."""
    if not state.session.answers:
        return
    with ui.column().classes("w-full max-w-5xl gap-3"):
        ui.label("Assessment memory").classes("text-xs uppercase tracking-widest hc-muted mt-4")
        for index, answer in enumerate(state.session.answers, start=1):
            with flat_card("w-full"):
                with ui.row().classes("items-start justify-between gap-4 w-full"):
                    with ui.column().classes("gap-1"):
                        ui.label(f"{index:02d}. {answer.question}").classes("font-semibold")
                        ui.label(answer.answer).classes("hc-muted leading-6")
                    ui.label(answer.source.upper()).classes("text-xs tracking-widest hc-accent")


@ui.page("/report")
def report_page() -> None:
    """Render the professional clinical report."""
    set_active_client()
    sidebar("Clinical Report")
    with ui.column().classes("hc-shell ml-0 md:ml-72 px-6 py-10 gap-8"):
        if not state.report_sections:
            editorial_header("No report yet", "Complete the adaptive assessment to generate a clinical report.")
            primary_button("Go to Assessment", on_click=lambda: ui.navigate.to("/patient"), icon="stethoscope")
            return

        patient = state.session.patient_summary()
        editorial_header(
            "Clinical assessment report",
            f"Prepared for {patient.get('full_name')} from {patient.get('answered_questions')} structured assessment answers.",
        )

        with ui.row().classes("gap-4 flex-wrap"):
            metric("Patient", str(patient.get("full_name")), str(patient.get("gender")))
            metric("Age", str(patient.get("age")), "Reported")
            metric("Risk", str(patient.get("risk_level")), "Preliminary")

        with ui.row().classes("gap-3"):
            secondary_button(
                "Copy Report",
                on_click=lambda: ui.run_javascript(
                    f"navigator.clipboard.writeText({sections_to_markdown(state.report_sections)!r})"
                ),
                icon="content_copy",
            )

            def download() -> None:
                md_path, csv_path = export_report(patient, state.report_sections)
                notify(f"Report saved: {md_path.name} and {csv_path.name}", "positive")

            secondary_button("Download Report", on_click=download, icon="download")
            secondary_button("New Assessment", on_click=reset_assessment, icon="restart_alt")

        with ui.column().classes("gap-5 w-full hc-report"):
            for section in state.report_sections:
                with card("w-full"):
                    ui.label(section.title).classes("hc-serif text-3xl")
                    ui.markdown(section.content).classes("mt-3 leading-7")


def reset_assessment() -> None:
    """Reset assessment and report state."""
    state.session.reset()
    state.report_sections = []
    state.processing = False
    state.assessment_error = ""
    ui.navigate.to("/patient")


if __name__ in {"__main__", "__mp_main__"}:
    port = int(os.getenv("PORT", 8080))
    ui.run(title="Health Companion", reload=False, host="0.0.0.0", port=port)


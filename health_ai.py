"""Gemini integration for Health Companion."""

from __future__ import annotations

from dataclasses import dataclass
import time

from google import genai
from google.genai import types

from config import DEFAULT_AI_MAX_OUTPUT_TOKENS, DEFAULT_AI_RESPONSE_STYLE, DEFAULT_AI_TEMPERATURE


GEMINI_REQUEST_TIMEOUT_SECONDS = 15


class HealthAiError(RuntimeError):
    """Raised when Gemini assessment generation fails."""


@dataclass(frozen=True)
class GeminiModelInfo:
    """Metadata for a Gemini model available to the current API key."""

    name: str
    display_name: str
    description: str
    output_token_limit: int | None = None
    max_temperature: float | None = None
    supported_actions: tuple[str, ...] = ()


@dataclass(frozen=True)
class GeminiGenerationSettings:
    """Session-scoped generation settings for Gemini requests."""

    model_name: str
    temperature: float = DEFAULT_AI_TEMPERATURE
    max_output_tokens: int = DEFAULT_AI_MAX_OUTPUT_TOKENS
    response_style: str = DEFAULT_AI_RESPONSE_STYLE


@dataclass(frozen=True)
class GeminiConnectionResult:
    """Structured result for the AI connection test."""

    success: bool
    message: str
    response_time_ms: int | None = None
    model_name: str = ""
    details: str = ""


@dataclass
class GeminiHealthClient:
    """Small Gemini client that keeps the API key in memory only."""

    api_key: str

    def validate_api_key(self) -> None:
        """Validate credentials by listing models for the current key."""
        try:
            list(genai.Client(api_key=self.api_key).models.list())
        except Exception as exc:
            raise HealthAiError(_friendly_error_message(exc, "Could not validate the Gemini API key.")) from exc

    def list_text_models(self) -> list[GeminiModelInfo]:
        """Return only Gemini models that support text generation."""
        try:
            client = genai.Client(api_key=self.api_key)
            models = list(client.models.list())
        except Exception as exc:
            raise HealthAiError(_friendly_error_message(exc, "Could not load Gemini models.")) from exc

        filtered: list[GeminiModelInfo] = []
        for model in models:
            try:
                if not _supports_text_generation_sdk(model):
                    continue
                filtered.append(
                    GeminiModelInfo(
                        name=model.name or "",
                        display_name=_pretty_model_name(model.display_name or "", model.name or ""),
                        description=model.description or "",
                        output_token_limit=model.output_token_limit,
                        max_temperature=None,
                        supported_actions=tuple(model.supported_actions or []),
                    )
                )
            except Exception:
                continue

        return _rank_models(filtered)

    def test_connection(self, settings: GeminiGenerationSettings) -> GeminiConnectionResult:
        """Run a tiny generation request using the selected model."""
        started = time.perf_counter()
        try:
            response = self._generate_content(
                "Return exactly: Health Companion ready",
                settings,
                temperature_override=0.0,
                max_output_tokens_override=64,
            )
        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            return GeminiConnectionResult(
                success=False,
                message=_friendly_error_message(exc, "AI connection test failed."),
                response_time_ms=elapsed_ms,
                model_name=settings.model_name,
                details=str(exc),
            )

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return GeminiConnectionResult(
            success=bool(response.strip()),
            message="Connection successful." if response.strip() else "Gemini returned an empty response.",
            response_time_ms=elapsed_ms,
            model_name=settings.model_name,
            details=response.strip(),
        )

    def generate_report(self, prompt: str, settings: GeminiGenerationSettings) -> str:
        """Generate a structured health report from a validated prompt."""
        try:
            response = self._generate_content(prompt, settings, response_mime_type="application/json")
        except Exception as exc:
            raise HealthAiError(_friendly_error_message(exc, "Gemini report generation failed.")) from exc

        text = response.strip()
        if not text:
            raise HealthAiError("Gemini returned an empty report.")
        return text

    def _generate_content(
        self,
        prompt: str,
        settings: GeminiGenerationSettings,
        *,
        response_mime_type: str | None = None,
        temperature_override: float | None = None,
        max_output_tokens_override: int | None = None,
    ) -> str:
        try:
            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model=settings.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=settings.temperature if temperature_override is None else temperature_override,
                    top_p=0.9,
                    max_output_tokens=settings.max_output_tokens if max_output_tokens_override is None else max_output_tokens_override,
                    response_mime_type=response_mime_type,
                    system_instruction=_system_instruction_for_style(settings.response_style),
                ),
            )
        except Exception as exc:
            raise HealthAiError(_friendly_error_message(exc, "Gemini request failed.")) from exc

        return (response.text or "").strip()


def _supports_text_generation_sdk(model) -> bool:
    """Check if model supports text generation."""
    actions = [str(action).lower() for action in (model.supported_actions or []) if str(action).strip()]
    if actions and not any("generate" in action for action in actions):
        return False

    searchable = " ".join(
        str(part) for part in (model.name or "", model.display_name or "", model.description or "")
    ).lower()
    blocked_tokens = ("embed", "image", "video", "audio", "speech", "embedding")
    return not any(token in searchable for token in blocked_tokens)


def _pretty_model_name(display_name: str, resource_name: str) -> str:
    if display_name.strip():
        return display_name.strip()
    short_name = resource_name.split("/")[-1].replace("-", " ").strip()
    return short_name.title() if short_name else "Gemini Model"


def _rank_models(models: list[GeminiModelInfo]) -> list[GeminiModelInfo]:
    def sort_key(model: GeminiModelInfo) -> tuple[int, int, str]:
        name = f"{model.name} {model.display_name} {model.description}".lower()
        is_flash = int("flash" not in name)
        is_pro = int("pro" not in name)
        token_rank = -(model.output_token_limit or 0)
        return (is_flash, is_pro, token_rank, model.display_name.lower())

    return sorted(models, key=sort_key)


def _system_instruction_for_style(style: str) -> str:
    normalized = style.strip().lower()
    if normalized == "simple":
        return "Use simple, direct language that is easy for a patient to understand."
    if normalized == "detailed":
        return "Provide more detailed but still concise medical output with clear structure."
    if normalized == "technical":
        return "Use precise clinical terminology and a technical medical tone."
    return "Use calm, professional medical language suitable for a clinical assessment product."


def _friendly_error_message(exc: Exception, fallback_message: str) -> str:
    raw_message = str(exc).strip()
    lowered = raw_message.lower()

    if any(token in lowered for token in ("unauthenticated", "invalid api key", "api key", "expired", "permission denied", "403", "401")):
        return "Invalid or expired API key. Please check the key in AI Settings and try again."

    if any(token in lowered for token in ("quota", "resource_exhausted", "rate limit", "429")):
        return "Gemini quota or rate limit reached. Please wait and try again."

    if any(token in lowered for token in ("timeout", "deadline", "timed out")):
        return "The request timed out while contacting Gemini. Please try again."

    if any(token in lowered for token in ("network", "connection refused", "dns", "no internet", "name or service not known", "unavailable")):
        return "Network error while contacting Gemini. Check your internet connection and try again."

    if any(token in lowered for token in ("model", "not found", "404", "unsupported")):
        return "Selected model is unavailable for this API key or project. Choose another model and try again."

    if raw_message:
        return f"{fallback_message} {raw_message}"
    return fallback_message


from __future__ import annotations

import json
from typing import Any

import httpx

from app.config import Settings
from app.exceptions import TranslationError
from app.providers.base import TranslationProvider
from app.providers.prompts import build_translation_prompt, extract_translation

GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
TIMEOUT_MESSAGE = "The Gemini API request timed out. Try again or use a shorter passage."
UNAVAILABLE_MESSAGE = "The Gemini API is unavailable. Check the API key, model, and quota."
MALFORMED_MESSAGE = "The Gemini API returned an unusable response. No translation was invented."


class GeminiProvider(TranslationProvider):
    def __init__(self, settings: Settings, client: httpx.AsyncClient) -> None:
        self._settings = settings
        self._client = client

    @property
    def name(self) -> str:
        return "gemini"

    async def translate(
        self,
        *,
        text: str,
        source_language: str,
        target_language: str,
        mode: str,
    ) -> str:
        return await self.generate(
            prompt=build_translation_prompt(
                text=text,
                source_language=source_language,
                target_language=target_language,
                mode=mode,
            ),
            temperature=0.2 if mode == "advanced" else 0.1,
        )

    async def generate(self, *, prompt: str, temperature: float = 0.1) -> str:
        if not self._settings.gemini_api_key.strip():
            raise TranslationError(
                "Gemini is selected but GEMINI_API_KEY is not configured.",
                status_code=503,
                code="provider_not_configured",
            )

        url = (
            f"{GEMINI_API_BASE_URL}/models/"
            f"{self._settings.gemini_model}:generateContent"
        )
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": temperature,
            },
        }
        timeout = httpx.Timeout(self._settings.gemini_timeout_seconds, connect=5.0)

        try:
            response = await self._client.post(
                url,
                json=payload,
                headers={"x-goog-api-key": self._settings.gemini_api_key},
                timeout=timeout,
            )
        except httpx.TimeoutException as exc:
            raise TranslationError(TIMEOUT_MESSAGE, status_code=504, code="timeout") from exc
        except httpx.RequestError as exc:
            raise TranslationError(
                UNAVAILABLE_MESSAGE,
                status_code=503,
                code="provider_unavailable",
            ) from exc

        return self._parse_response(response)

    def _parse_response(self, response: httpx.Response) -> str:
        if response.status_code == 429:
            raise TranslationError(
                "The Gemini API quota or rate limit was reached. Try again later or check your quota.",
                status_code=503,
                code="provider_rate_limited",
            )
        if response.status_code in {401, 403}:
            raise TranslationError(
                "Gemini rejected the API key. Check GEMINI_API_KEY and its API access.",
                status_code=503,
                code="provider_configuration",
            )
        if response.status_code >= 400:
            raise TranslationError(
                UNAVAILABLE_MESSAGE,
                status_code=503,
                code="provider_unavailable",
            )

        try:
            data: dict[str, Any] = response.json()
        except (json.JSONDecodeError, ValueError) as exc:
            raise TranslationError(
                MALFORMED_MESSAGE,
                status_code=502,
                code="malformed_response",
            ) from exc

        candidates = data.get("candidates") if isinstance(data, dict) else None
        if not isinstance(candidates, list) or not candidates:
            raise TranslationError(
                MALFORMED_MESSAGE,
                status_code=502,
                code="malformed_response",
            )

        content = candidates[0].get("content") if isinstance(candidates[0], dict) else None
        parts = content.get("parts") if isinstance(content, dict) else None
        if not isinstance(parts, list):
            raise TranslationError(
                MALFORMED_MESSAGE,
                status_code=502,
                code="malformed_response",
            )

        text_parts = [
            part["text"]
            for part in parts
            if isinstance(part, dict)
            and isinstance(part.get("text"), str)
            and not part.get("thought", False)
        ]
        translated = extract_translation("\n".join(text_parts))
        if not translated:
            raise TranslationError(
                MALFORMED_MESSAGE,
                status_code=502,
                code="malformed_response",
            )
        return translated

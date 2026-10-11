from __future__ import annotations

import json
from typing import Any

import httpx

from app.config import Settings
from app.exceptions import TranslationError
from app.providers.base import TranslationProvider
from app.providers.prompts import (
    build_translation_prompt as build_prompt,
    extract_translation,
)

UNAVAILABLE_MESSAGE = (
    "The AI model is unavailable. Start Ollama locally and pull the configured model."
)
TIMEOUT_MESSAGE = "The translation model timed out. Try a shorter passage or try again."
MALFORMED_MESSAGE = "The translation model returned an unusable response. No translation was invented."


class OllamaProvider(TranslationProvider):
    def __init__(self, settings: Settings, client: httpx.AsyncClient) -> None:
        self._settings = settings
        self._client = client

    @property
    def name(self) -> str:
        return "ollama"

    async def translate(
        self,
        *,
        text: str,
        source_language: str,
        target_language: str,
        mode: str,
    ) -> str:
        return await self.generate(
            prompt=build_prompt(
                text=text,
                source_language=source_language,
                target_language=target_language,
                mode=mode,
            ),
            temperature=0.2 if mode == "advanced" else 0.1,
        )

    async def generate(self, *, prompt: str, temperature: float = 0.1) -> str:
        payload = {
            "model": self._settings.ollama_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }

        try:
            response = await self._client.post(
                f"{self._settings.ollama_base_url.rstrip('/')}/api/generate",
                json=payload,
            )
        except httpx.TimeoutException as exc:
            raise TranslationError(TIMEOUT_MESSAGE, status_code=504, code="timeout") from exc
        except httpx.RequestError as exc:
            raise TranslationError(
                UNAVAILABLE_MESSAGE,
                status_code=503,
                code="model_unavailable",
            ) from exc

        return self._parse_response(response)

    def _parse_response(self, response: httpx.Response) -> str:
        if response.status_code == 404:
            raise TranslationError(
                UNAVAILABLE_MESSAGE,
                status_code=503,
                code="model_unavailable",
            )

        if response.status_code >= 400:
            raise TranslationError(
                UNAVAILABLE_MESSAGE,
                status_code=503,
                code="model_unavailable",
            )

        try:
            data: dict[str, Any] = response.json()
        except json.JSONDecodeError as exc:
            raise TranslationError(
                MALFORMED_MESSAGE,
                status_code=502,
                code="malformed_response",
            ) from exc

        if not isinstance(data, dict):
            raise TranslationError(
                MALFORMED_MESSAGE,
                status_code=502,
                code="malformed_response",
            )

        if data.get("error"):
            raise TranslationError(
                UNAVAILABLE_MESSAGE,
                status_code=503,
                code="model_unavailable",
            )

        raw = data.get("response")
        if not isinstance(raw, str):
            raise TranslationError(
                MALFORMED_MESSAGE,
                status_code=502,
                code="malformed_response",
            )

        translated = extract_translation(raw)
        if not translated:
            raise TranslationError(
                MALFORMED_MESSAGE,
                status_code=502,
                code="malformed_response",
            )
        return translated

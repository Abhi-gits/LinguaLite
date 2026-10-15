import json

import httpx
import pytest

from app.config import Settings
from app.exceptions import TranslationError
from app.providers.factory import create_provider
from app.providers.gemini import GeminiProvider


class _SequenceTransport(httpx.AsyncBaseTransport):
    def __init__(self, handler) -> None:
        self._handler = handler
        self.requests: list[httpx.Request] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return await self._handler(request)


def _settings(**overrides: str) -> Settings:
    values = {
        "translation_provider": "gemini",
        "gemini_api_key": "test-secret",
        "gemini_model": "gemini-test",
        "gemini_timeout_seconds": 2.0,
    }
    values.update(overrides)
    return Settings(**values)


async def _translate_with(handler, **kwargs) -> tuple[str, _SequenceTransport]:
    transport = _SequenceTransport(handler)
    async with httpx.AsyncClient(transport=transport, timeout=2.0) as client:
        provider = GeminiProvider(_settings(), client)
        result = await provider.translate(
            text=kwargs.get("text", "Hello"),
            source_language=kwargs.get("source_language", "en"),
            target_language=kwargs.get("target_language", "hi"),
            mode=kwargs.get("mode", "simple"),
        )
    return result, transport


@pytest.mark.asyncio
async def test_success_sends_translation_prompt_and_api_key_header() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {"text": "internal reasoning", "thought": True},
                                {"text": "नमस्ते"},
                            ]
                        }
                    }
                ]
            },
        )

    result, transport = await _translate_with(handler, mode="advanced")

    assert result == "नमस्ते"
    request = transport.requests[0]
    assert request.url.path.endswith("/models/gemini-test:generateContent")
    assert request.url.query == b""
    assert request.headers["x-goog-api-key"] == "test-secret"
    body = json.loads(request.content.decode())
    prompt = body["contents"][0]["parts"][0]["text"]
    assert "English (en)" in prompt
    assert "Hindi (hi)" in prompt
    assert "Advanced mode" in prompt
    assert body["generationConfig"]["temperature"] == 0.2


@pytest.mark.asyncio
async def test_missing_api_key_fails_without_request() -> None:
    transport = _SequenceTransport(
        lambda _request: httpx.Response(200, json={})
    )
    async with httpx.AsyncClient(transport=transport) as client:
        provider = GeminiProvider(_settings(gemini_api_key=""), client)
        with pytest.raises(TranslationError) as exc:
            await provider.translate(
                text="Hello",
                source_language="en",
                target_language="hi",
                mode="simple",
            )

    assert exc.value.code == "provider_not_configured"
    assert not transport.requests


@pytest.mark.asyncio
async def test_timeout_is_reported() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out")

    with pytest.raises(TranslationError) as exc:
        await _translate_with(handler)

    assert exc.value.code == "timeout"
    assert exc.value.status_code == 504


@pytest.mark.asyncio
async def test_rate_limit_is_reported_without_provider_details() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"message": "quota details"}})

    with pytest.raises(TranslationError) as exc:
        await _translate_with(handler)

    assert exc.value.code == "provider_rate_limited"
    assert "quota details" not in exc.value.message


@pytest.mark.asyncio
async def test_invalid_key_is_reported_without_echoing_key() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"error": {"message": "invalid key"}})

    with pytest.raises(TranslationError) as exc:
        await _translate_with(handler)

    assert exc.value.code == "provider_configuration"
    assert "test-secret" not in exc.value.message


@pytest.mark.asyncio
async def test_retired_model_error_is_reported_with_recovery_guidance() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            404,
            json={
                "error": {
                    "status": "NOT_FOUND",
                    "message": "This model is no longer available to new users.",
                }
            },
        )

    with pytest.raises(TranslationError) as exc:
        await _translate_with(handler)

    assert exc.value.code == "provider_model_unavailable"
    assert "GEMINI_MODEL" in exc.value.message
    assert "gemini-3.8-flash" in exc.value.message


@pytest.mark.asyncio
async def test_malformed_response_does_not_invent_translation() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"candidates": []})

    with pytest.raises(TranslationError) as exc:
        await _translate_with(handler)

    assert exc.value.code == "malformed_response"
    assert exc.value.status_code == 502


@pytest.mark.asyncio
async def test_factory_creates_gemini_only_when_explicitly_selected() -> None:
    settings = _settings()
    async with httpx.AsyncClient() as client:
        provider = create_provider(settings, client)

    assert isinstance(provider, GeminiProvider)
    assert provider.name == "gemini"

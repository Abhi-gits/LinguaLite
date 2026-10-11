import json

import httpx
import pytest

from app.config import Settings
from app.exceptions import TranslationError
from app.providers.factory import create_provider
from app.providers.ollama import OllamaProvider, build_prompt, extract_translation


class _SequenceTransport(httpx.AsyncBaseTransport):
    def __init__(self, handler) -> None:
        self._handler = handler
        self.requests: list[httpx.Request] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return await self._handler(request)


def _settings() -> Settings:
    return Settings(
        ollama_base_url="http://ollama.test",
        ollama_model="deepseek-r1:latest",
        ollama_timeout_seconds=1.0,
    )


async def _translate_with(handler, **kwargs) -> tuple[str, _SequenceTransport]:
    transport = _SequenceTransport(handler)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://ollama.test",
        timeout=1.0,
    ) as client:
        provider = OllamaProvider(_settings(), client)
        result = await provider.translate(
            text=kwargs.get("text", "Hello"),
            source_language=kwargs.get("source_language", "en"),
            target_language=kwargs.get("target_language", "hi"),
            mode=kwargs.get("mode", "simple"),
        )
    return result, transport


@pytest.mark.asyncio
async def test_successful_translation_uses_language_pair_and_mode() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"response": "नमस्ते", "done": True})

    result, transport = await _translate_with(handler, mode="advanced")
    assert result == "नमस्ते"
    assert len(transport.requests) == 1
    body = json.loads(transport.requests[0].content.decode())
    assert body["model"] == "deepseek-r1:latest"
    assert body["stream"] is False
    prompt = body["prompt"]
    assert "English (en)" in prompt
    assert "Hindi (hi)" in prompt
    assert "Advanced mode" in prompt
    assert "Hello" in prompt


@pytest.mark.asyncio
async def test_timeout_does_not_invent_translation() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out")

    with pytest.raises(TranslationError) as exc:
        await _translate_with(handler)

    assert exc.value.code == "timeout"
    assert exc.value.status_code == 504


@pytest.mark.asyncio
async def test_connection_error_is_model_unavailable() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    with pytest.raises(TranslationError) as exc:
        await _translate_with(handler)

    assert exc.value.code == "model_unavailable"
    assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_missing_model_is_unavailable() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "model 'deepseek-r1:latest' not found"})

    with pytest.raises(TranslationError) as exc:
        await _translate_with(handler)

    assert exc.value.code == "model_unavailable"


@pytest.mark.asyncio
async def test_malformed_json_is_rejected() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not-json")

    with pytest.raises(TranslationError) as exc:
        await _translate_with(handler)

    assert exc.value.code == "malformed_response"
    assert exc.value.status_code == 502


@pytest.mark.asyncio
async def test_missing_response_field_is_rejected() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"done": True})

    with pytest.raises(TranslationError) as exc:
        await _translate_with(handler)

    assert exc.value.code == "malformed_response"


@pytest.mark.asyncio
async def test_empty_model_output_is_rejected() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"response": "   "})

    with pytest.raises(TranslationError) as exc:
        await _translate_with(handler)

    assert exc.value.code == "malformed_response"


def test_extract_translation_strips_fences() -> None:
    assert extract_translation('```\nनमस्ते\n```') == "नमस्ते"


def test_simple_prompt_asks_for_translation_only() -> None:
    prompt = build_prompt(
        text="Hello",
        source_language="en",
        target_language="hi",
        mode="simple",
    )
    assert "Simple mode" in prompt
    assert "only the translation" in prompt.lower() or "Return only the translation" in prompt


def test_factory_rejects_unknown_provider() -> None:
    settings = Settings(translation_provider="openai")
    with pytest.raises(ValueError, match="explicitly"):
        create_provider(settings, httpx.AsyncClient())

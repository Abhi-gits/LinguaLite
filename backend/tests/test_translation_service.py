from unittest.mock import AsyncMock, MagicMock

import pytest

from app.exceptions import TranslationError
from app.schemas import TranslationRequest
from app.services.translation import TranslationService


@pytest.mark.asyncio
async def test_service_returns_provider_metadata() -> None:
    provider = MagicMock()
    provider.name = "ollama"
    provider.translate = AsyncMock(return_value="नमस्ते")
    service = TranslationService(provider)
    request = TranslationRequest(
        text="Hello",
        source_language="en",
        target_language="hi",
        mode="simple",
    )

    result = await service.translate(request)

    assert result.translated_text == "नमस्ते"
    assert result.provider == "ollama"
    provider.translate.assert_awaited_once_with(
        text="Hello",
        source_language="en",
        target_language="hi",
        mode="simple",
    )


@pytest.mark.asyncio
async def test_service_rejects_blank_provider_output() -> None:
    provider = MagicMock()
    provider.name = "ollama"
    provider.translate = AsyncMock(return_value="  ")
    service = TranslationService(provider)
    request = TranslationRequest(
        text="Hello",
        source_language="en",
        target_language="hi",
        mode="simple",
    )

    with pytest.raises(TranslationError) as exc:
        await service.translate(request)

    assert exc.value.code == "malformed_response"


@pytest.mark.asyncio
async def test_auto_detects_hindi_and_returns_resolved_source_language() -> None:
    provider = MagicMock()
    provider.name = "ollama"
    provider.generate = AsyncMock(return_value="hi")
    provider.translate = AsyncMock(return_value="Hello")
    service = TranslationService(provider)
    request = TranslationRequest(
        text="नमस्ते",
        source_language="auto",
        target_language="en",
        mode="simple",
    )

    result = await service.translate(request)

    assert result.source_language == "hi"
    assert result.translated_text == "Hello"
    provider.generate.assert_awaited_once()
    provider.translate.assert_awaited_once_with(
        text="नमस्ते",
        source_language="hi",
        target_language="en",
        mode="simple",
    )


@pytest.mark.asyncio
async def test_auto_detection_rejects_unsupported_detected_language() -> None:
    provider = MagicMock()
    provider.generate = AsyncMock(return_value="fr")
    provider.translate = AsyncMock()
    service = TranslationService(provider)
    request = TranslationRequest(
        text="Bonjour",
        source_language="auto",
        target_language="hi",
        mode="simple",
    )

    with pytest.raises(TranslationError) as exc:
        await service.translate(request)

    assert exc.value.code == "unsupported_source_language"
    provider.translate.assert_not_awaited()


@pytest.mark.asyncio
async def test_auto_detection_rejects_unsupported_language_pair() -> None:
    provider = MagicMock()
    provider.generate = AsyncMock(return_value="en")
    provider.translate = AsyncMock()
    service = TranslationService(provider)
    request = TranslationRequest(
        text="Hello",
        source_language="auto",
        target_language="en",
        mode="simple",
    )

    with pytest.raises(TranslationError) as exc:
        await service.translate(request)

    assert exc.value.code == "unsupported_language_pair"
    provider.translate.assert_not_awaited()

import pytest
from pydantic import ValidationError

from app.constants import (
    EXPERIMENTAL_LANGUAGES,
    MAX_TEXT_LENGTH,
    SUPPORTED_LANGUAGES,
    SUPPORTED_TRANSLATION_PAIRS,
)
from app.schemas import AssistantRequest, TranslationRequest


def test_valid_english_to_hindi_request() -> None:
    request = TranslationRequest(
        text="  Hello world  ",
        source_language="EN",
        target_language="hi",
        mode="Simple",
    )
    assert request.text == "Hello world"
    assert request.source_language == "en"
    assert request.target_language == "hi"
    assert request.mode == "simple"


def test_valid_hindi_to_english_advanced_request() -> None:
    request = TranslationRequest(
        text="नमस्ते",
        source_language="hi",
        target_language="en",
        mode="advanced",
    )
    assert request.mode == "advanced"


def test_auto_source_language_is_valid() -> None:
    request = TranslationRequest(
        text="नमस्ते",
        source_language="AUTO",
        target_language="en",
        mode="simple",
    )
    assert request.source_language == "auto"


def test_auto_target_language_is_rejected() -> None:
    with pytest.raises(ValidationError, match="Target language must be selected"):
        TranslationRequest(
            text="Hello",
            source_language="auto",
            target_language="auto",
            mode="simple",
        )


def test_identical_source_and_target_are_rejected() -> None:
    with pytest.raises(ValidationError, match="must be different"):
        TranslationRequest(
            text="Hello",
            source_language="en",
            target_language="en",
            mode="simple",
        )


def test_empty_text_is_rejected() -> None:
    with pytest.raises(ValidationError) as exc:
        TranslationRequest(
            text="   ",
            source_language="en",
            target_language="hi",
            mode="simple",
        )
    assert "empty" in str(exc.value).lower()


def test_missing_text_is_rejected() -> None:
    with pytest.raises(ValidationError):
        TranslationRequest(
            source_language="en",
            target_language="hi",
            mode="simple",
        )


def test_unsupported_language_is_rejected() -> None:
    with pytest.raises(ValidationError) as exc:
        TranslationRequest(
            text="Hello",
            source_language="fr",
            target_language="en",
            mode="simple",
        )
    assert "unsupported language" in str(exc.value).lower()


def test_same_source_and_target_are_rejected() -> None:
    with pytest.raises(ValidationError) as exc:
        TranslationRequest(
            text="Hello",
            source_language="en",
            target_language="en",
            mode="simple",
        )
    assert "must be different" in str(exc.value).lower()


def test_invalid_mode_is_rejected() -> None:
    with pytest.raises(ValidationError):
        TranslationRequest(
            text="Hello",
            source_language="en",
            target_language="hi",
            mode="literal",
        )


def test_excessively_long_text_is_rejected() -> None:
    with pytest.raises(ValidationError) as exc:
        TranslationRequest(
            text="a" * (MAX_TEXT_LENGTH + 1),
            source_language="en",
            target_language="hi",
            mode="simple",
        )
    assert "at most" in str(exc.value).lower() or "max" in str(exc.value).lower()


def test_all_indian_languages_are_registered_and_pairs_are_enabled() -> None:
    assert set(EXPERIMENTAL_LANGUAGES) == {"ta", "te", "kn", "ml", "bn", "mr", "gu", "pa"}
    assert len(SUPPORTED_LANGUAGES) == 10
    assert len(SUPPORTED_TRANSLATION_PAIRS) == len(SUPPORTED_LANGUAGES) * (
        len(SUPPORTED_LANGUAGES) - 1
    )
    assert all(source != target for source, target in SUPPORTED_TRANSLATION_PAIRS)


def test_translation_accepts_regional_to_regional_pair() -> None:
    request = TranslationRequest(
        text="வணக்கம்",
        source_language="ta",
        target_language="bn",
        mode="simple",
    )

    assert request.source_language == "ta"
    assert request.target_language == "bn"


def test_india_connect_requires_different_supported_languages() -> None:
    request = AssistantRequest(
        task="india_connect",
        text="Ask for the nearest bus stop.",
        source_language="en",
        target_language="te",
        audience="service_staff",
    )

    assert request.task == "india_connect"
    assert request.target_language == "te"

    with pytest.raises(ValidationError, match="must be different"):
        AssistantRequest(
            task="india_connect",
            text="Say hello.",
            source_language="ta",
            target_language="ta",
        )

import pytest
from pydantic import ValidationError

from app.constants import MAX_TEXT_LENGTH
from app.schemas import TranslationRequest


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

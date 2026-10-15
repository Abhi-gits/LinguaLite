from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from app.constants import MAX_TEXT_LENGTH
from app.exceptions import TranslationError
from app.main import create_app
from app.services.translation import TranslationService


def _payload(**overrides: str) -> dict[str, str]:
    data = {
        "text": "Hello",
        "source_language": "en",
        "target_language": "hi",
        "mode": "simple",
    }
    data.update(overrides)
    return data


def test_translate_success(api_client: TestClient, mock_provider: MagicMock) -> None:
    response = api_client.post("/api/translate", json=_payload())

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "translated_text": "नमस्ते",
        "source_language": "en",
        "target_language": "hi",
        "mode": "simple",
        "provider": "ollama",
        "early_access": False,
    }
    mock_provider.translate.assert_awaited_once_with(
        text="Hello",
        source_language="en",
        target_language="hi",
        mode="simple",
    )


def test_translate_passes_advanced_hindi_to_english(
    api_client: TestClient, mock_provider: MagicMock
) -> None:
    mock_provider.translate.return_value = "Hello"
    response = api_client.post(
        "/api/translate",
        json=_payload(text="नमस्ते", source_language="hi", target_language="en", mode="advanced"),
    )

    assert response.status_code == 200
    assert response.json()["mode"] == "advanced"
    mock_provider.translate.assert_awaited_once_with(
        text="नमस्ते",
        source_language="hi",
        target_language="en",
        mode="advanced",
    )


def test_translate_allows_regional_pair_and_marks_early_access(
    api_client: TestClient, mock_provider: MagicMock
) -> None:
    response = api_client.post(
        "/api/translate",
        json=_payload(text="வணக்கம்", source_language="ta", target_language="gu"),
    )

    assert response.status_code == 200
    assert response.json()["early_access"] is True
    mock_provider.translate.assert_awaited_once_with(
        text="வணக்கம்",
        source_language="ta",
        target_language="gu",
        mode="simple",
    )


def test_empty_input_returns_validation_error(api_client: TestClient) -> None:
    response = api_client.post("/api/translate", json=_payload(text="   "))
    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "invalid_request"
    assert "traceback" not in body["message"].lower()
    assert "enter text" in body["message"].lower() or "empty" in body["message"].lower()


def test_long_input_returns_validation_error(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/translate",
        json=_payload(text="x" * (MAX_TEXT_LENGTH + 1)),
    )
    assert response.status_code == 422
    assert response.json()["error"] == "invalid_request"
    assert "too long" in response.json()["message"].lower()


def test_configured_max_text_length_is_enforced(
    settings, mock_provider: MagicMock
) -> None:
    settings.max_text_length = 4
    app = create_app(settings=settings, service=TranslationService(mock_provider))
    with TestClient(app) as client:
        response = client.post("/api/translate", json=_payload(text="Hello"))

    assert response.status_code == 422
    assert response.json() == {
        "error": "invalid_request",
        "message": "Text is too long. Use 4 characters or fewer.",
    }
    mock_provider.translate.assert_not_awaited()


def test_model_unavailable(api_client: TestClient, mock_provider: MagicMock) -> None:
    mock_provider.translate = AsyncMock(
        side_effect=TranslationError(
            "The AI model is unavailable. Start Ollama locally and pull the configured model.",
            status_code=503,
            code="model_unavailable",
        )
    )
    response = api_client.post("/api/translate", json=_payload())
    assert response.status_code == 503
    body = response.json()
    assert body["error"] == "model_unavailable"
    assert "unavailable" in body["message"].lower()
    assert "traceback" not in str(body).lower()
    assert "Traceback" not in response.text


def test_timeout(api_client: TestClient, mock_provider: MagicMock) -> None:
    mock_provider.translate = AsyncMock(
        side_effect=TranslationError(
            "The translation model timed out. Try a shorter passage or try again.",
            status_code=504,
            code="timeout",
        )
    )
    response = api_client.post("/api/translate", json=_payload())
    assert response.status_code == 504
    assert response.json()["error"] == "timeout"


def test_malformed_response(api_client: TestClient, mock_provider: MagicMock) -> None:
    mock_provider.translate = AsyncMock(
        side_effect=TranslationError(
            "The translation model returned an unusable response. No translation was invented.",
            status_code=502,
            code="malformed_response",
        )
    )
    response = api_client.post("/api/translate", json=_payload())
    assert response.status_code == 502
    assert response.json()["error"] == "malformed_response"


def test_unhandled_error_does_not_expose_stack_trace(settings, caplog) -> None:
    provider = MagicMock()
    provider.name = "ollama"
    provider.translate = AsyncMock(side_effect=RuntimeError("secret internal failure"))
    app = create_app(settings=settings, service=TranslationService(provider))

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/api/translate", json=_payload())

    assert response.status_code == 500
    body = response.json()
    assert body["error"] == "internal_error"
    assert "secret internal failure" not in response.text
    assert "Traceback" not in response.text
    assert "Unhandled application error" in caplog.text


def test_health_endpoint(api_client: TestClient) -> None:
    response = api_client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["provider"] == "ollama"


def test_health_reports_gemini_model(settings) -> None:
    settings.translation_provider = "gemini"
    settings.gemini_model = "gemini-test"
    provider = MagicMock()
    provider.name = "gemini"
    provider.translate = AsyncMock(return_value="नमस्ते")
    app = create_app(settings=settings, service=TranslationService(provider))

    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.json() == {
        "status": "ok",
        "provider": "gemini",
        "model": "gemini-test",
    }

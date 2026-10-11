from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.services.translation import TranslationService


def _app_client() -> tuple[TestClient, MagicMock]:
    provider = MagicMock()
    provider.name = "ollama"
    provider.translate = AsyncMock(return_value="नमस्ते")
    provider.generate = AsyncMock(return_value="नमस्ते")
    service = TranslationService(provider)
    app = create_app(
        settings=Settings(ollama_model="deepseek-r1:latest"),
        service=service,
    )
    return TestClient(app), provider


def test_assist_translation_returns_style_and_detected_source() -> None:
    client, provider = _app_client()
    provider.generate = AsyncMock(side_effect=["en", "नमस्ते"])

    with client:
        response = client.post(
            "/api/assist",
            json={
                "task": "translate",
                "text": "Hello",
                "source_language": "auto",
                "target_language": "hi",
                "style": "natural",
            },
        )

    assert response.status_code == 200
    assert response.json()["source_language"] == "en"
    assert response.json()["translated_text"] == "नमस्ते"
    assert response.json()["style"] == "natural"
    assert provider.generate.await_count == 2


@pytest.mark.parametrize(
    ("style", "instruction"),
    [
        ("natural", "natural, clear register"),
        ("formal", "formal, polished register"),
        ("casual", "casual, conversational register"),
        ("literal", "literally as possible"),
    ],
)
def test_translation_style_changes_model_instruction(style: str, instruction: str) -> None:
    client, provider = _app_client()
    with client:
        response = client.post(
            "/api/assist",
            json={
                "task": "translate",
                "text": "Hello",
                "source_language": "en",
                "target_language": "hi",
                "style": style,
            },
        )

    assert response.status_code == 200
    assert instruction in provider.generate.call_args.kwargs["prompt"]


def test_assist_grammar_preserves_language_and_returns_changes() -> None:
    client, provider = _app_client()
    provider.generate = AsyncMock(
        return_value='{"corrected_text":"I am going.","changes":"Fixed verb form."}'
    )

    with client:
        response = client.post(
            "/api/assist",
            json={
                "task": "grammar",
                "text": "I is going.",
                "source_language": "en",
            },
        )

    assert response.status_code == 200
    assert response.json()["corrected_text"] == "I am going."
    assert response.json()["changes"] == "Fixed verb form."
    assert "Do not translate" in provider.generate.call_args.kwargs["prompt"]


def test_assist_explanation_is_separate_from_original_text() -> None:
    client, provider = _app_client()
    provider.generate = AsyncMock(
        return_value='{"explanation":"This phrase is an informal greeting."}'
    )

    with client:
        response = client.post(
            "/api/assist",
            json={"task": "explain", "text": "What's up?", "source_language": "en"},
        )

    assert response.status_code == 200
    assert response.json()["explanation"] == "This phrase is an informal greeting."
    assert response.json()["translated_text"] is None


def test_assist_alternatives_deduplicates_primary_translation() -> None:
    client, provider = _app_client()
    provider.generate = AsyncMock(
        side_effect=[
            "सुप्रभात",
            (
                '{"alternatives":['
                '{"text":"सुप्रभात","nuance":"Same as main"},'
                '{"text":"शुभ प्रभात","nuance":"A little more formal"}]}'
            ),
        ]
    )

    with client:
        response = client.post(
            "/api/assist",
            json={
                "task": "translate",
                "text": "Good morning",
                "source_language": "en",
                "target_language": "hi",
                "alternatives": 2,
            },
        )

    assert response.status_code == 200
    assert response.json()["translated_text"] == "सुप्रभात"
    assert [item["text"] for item in response.json()["alternatives"]] == ["शुभ प्रभात"]


def test_assist_transliteration_is_distinct_from_translation() -> None:
    client, provider = _app_client()
    provider.generate = AsyncMock(
        return_value='{"transliterated_text":"namaste","note":"Colloquial romanization."}'
    )

    with client:
        response = client.post(
            "/api/assist",
            json={
                "task": "transliterate",
                "text": "नमस्ते",
                "source_language": "hi",
                "source_script": "devanagari",
                "target_script": "latin",
            },
        )

    assert response.status_code == 200
    assert response.json()["transliterated_text"] == "namaste"
    assert response.json()["task"] == "transliterate"
    assert response.json()["translated_text"] is None
    assert "do not translate" in provider.generate.call_args.kwargs["prompt"].lower()


@pytest.mark.parametrize(
    "payload",
    [
        {"task": "translate", "text": " ", "target_language": "hi"},
        {
            "task": "translate",
            "text": "Hello",
            "source_language": "en",
            "target_language": "en",
        },
        {
            "task": "translate",
            "text": "Hello",
            "source_language": "en",
            "target_language": "hi",
            "alternatives": 4,
        },
        {
            "task": "transliterate",
            "text": "hello",
            "source_language": "en",
            "target_script": "devanagari",
        },
    ],
)
def test_assist_rejects_invalid_task_parameters(payload: dict[str, object]) -> None:
    client, _provider = _app_client()
    with client:
        response = client.post("/api/assist", json=payload)

    assert response.status_code == 422
    assert response.json()["error"] == "invalid_request"


def test_assist_malformed_task_response_returns_error_not_fake_result() -> None:
    client, provider = _app_client()
    provider.generate = AsyncMock(return_value="not json")
    with client:
        response = client.post(
            "/api/assist",
            json={"task": "grammar", "text": "I is good.", "source_language": "en"},
        )

    assert response.status_code == 502
    assert response.json()["error"] == "malformed_response"
    assert response.json().get("corrected_text") is None

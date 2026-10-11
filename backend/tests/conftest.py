from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.services.translation import TranslationService


@pytest.fixture
def settings() -> Settings:
    return Settings(
        translation_provider="ollama",
        ollama_base_url="http://ollama.test",
        ollama_model="deepseek-r1:latest",
        ollama_timeout_seconds=2.0,
        cors_origins="http://localhost:5173",
    )


@pytest.fixture
def mock_provider() -> MagicMock:
    provider = MagicMock()
    provider.name = "ollama"
    provider.translate = AsyncMock(return_value="नमस्ते")
    return provider


@pytest.fixture
def api_client(settings: Settings, mock_provider: MagicMock) -> TestClient:
    service = TranslationService(mock_provider)
    app = create_app(settings=settings, service=service)
    with TestClient(app) as client:
        yield client

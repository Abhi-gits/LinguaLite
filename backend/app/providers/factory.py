import httpx

from app.config import Settings
from app.providers.base import TranslationProvider
from app.providers.gemini import GeminiProvider
from app.providers.ollama import OllamaProvider


def create_provider(settings: Settings, client: httpx.AsyncClient) -> TranslationProvider:
    """Build the configured provider.

    Gemini is only selected when TRANSLATION_PROVIDER explicitly requests it.
    """
    provider_name = settings.translation_provider.strip().lower()
    if provider_name == "ollama":
        return OllamaProvider(settings=settings, client=client)
    if provider_name == "gemini":
        return GeminiProvider(settings=settings, client=client)

    raise ValueError(
        f"Unknown translation provider '{settings.translation_provider}'. "
        "Choose 'ollama' or explicitly select and configure the 'gemini' provider."
    )

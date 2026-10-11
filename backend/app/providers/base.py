from abc import ABC, abstractmethod


class TranslationProvider(ABC):
    """Interface for local or hosted translation backends.

    Hosted providers must be selected explicitly through configuration.
    There is no automatic fallback to a paid API.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Stable identifier returned in API responses."""

    @abstractmethod
    async def generate(self, *, prompt: str, temperature: float = 0.1) -> str:
        """Generate model text for a task-specific prompt."""

    @abstractmethod
    async def translate(
        self,
        *,
        text: str,
        source_language: str,
        target_language: str,
        mode: str,
    ) -> str:
        """Return only the translated text, or raise TranslationError."""

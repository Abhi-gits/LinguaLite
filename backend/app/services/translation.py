from app.exceptions import TranslationError
from app.constants import SUPPORTED_LANGUAGES, SUPPORTED_TRANSLATION_PAIRS
from app.providers.base import TranslationProvider
from app.providers.prompts import build_translation_prompt
from app.providers.prompts import extract_translation
from app.schemas import TranslationRequest, TranslationResponse


class TranslationService:
    def __init__(self, provider: TranslationProvider) -> None:
        self.provider = provider

    async def translate(self, request: TranslationRequest) -> TranslationResponse:
        source_language = request.source_language
        if source_language == "auto":
            source_language = await self.detect_source_language(request.text)

        if (source_language, request.target_language) not in SUPPORTED_TRANSLATION_PAIRS:
            raise TranslationError(
                "The detected or selected source and target languages must be different.",
                status_code=422,
                code="unsupported_language_pair",
            )

        translated_text = await self.provider.translate(
            text=request.text,
            source_language=source_language,
            target_language=request.target_language,
            mode=request.mode,
        )
        if not translated_text or not translated_text.strip():
            raise TranslationError(
                "The translation model returned an unusable response. No translation was invented.",
                status_code=502,
                code="malformed_response",
            )

        return TranslationResponse(
            translated_text=translated_text.strip(),
            source_language=source_language,
            target_language=request.target_language,
            mode=request.mode,
            provider=self.provider.name,
        )

    async def translate_with_style(
        self,
        *,
        text: str,
        source_language: str,
        target_language: str,
        style: str,
    ) -> tuple[str, str]:
        resolved_source = (
            await self.detect_source_language(text)
            if source_language == "auto"
            else source_language
        )
        if (resolved_source, target_language) not in SUPPORTED_TRANSLATION_PAIRS:
            raise TranslationError(
                "The detected or selected source and target languages must be different.",
                status_code=422,
                code="unsupported_language_pair",
            )
        prompt = build_translation_prompt(
            text=text,
            source_language=resolved_source,
            target_language=target_language,
            style=style,
        )
        translated = extract_translation(
            await self.provider.generate(
                prompt=prompt,
                temperature=0.2 if style != "natural" else 0.1,
            )
        )
        if not translated:
            raise TranslationError(
                "The AI provider returned an unusable response. No translation was invented.",
                status_code=502,
                code="malformed_response",
            )
        return resolved_source, translated

    async def detect_source_language(self, text: str) -> str:
        language_options = ", ".join(
            f"{code} ({name})" for code, name in SUPPORTED_LANGUAGES.items()
        )
        prompt = (
            "Identify the primary language of the following text. "
            f"Choose only from: {language_options}. "
            "Return only the matching two-letter language code, with no other text. "
            "If the language is not one of those choices, return unsupported.\n\n"
            f"Text:\n{text}"
        )
        detected = (await self.provider.generate(prompt=prompt, temperature=0)).strip().lower()
        if detected not in SUPPORTED_LANGUAGES:
            raise TranslationError(
                "Could not identify a supported source language. Select a language manually "
                "or enter text in one of the listed languages.",
                status_code=422,
                code="unsupported_source_language",
            )
        return detected

from app.exceptions import TranslationError
from app.constants import SUPPORTED_TRANSLATION_PAIRS
from app.providers.base import TranslationProvider
from app.schemas import AssistantRequest, AssistantResponse
from app.services.alternatives import AlternativesService
from app.services.explanation import ExplanationService
from app.services.grammar import GrammarService
from app.services.india_connect import IndiaConnectService
from app.services.transliteration import TransliterationService
from app.services.translation import TranslationService


class WritingAssistantService:
    def __init__(self, provider: TranslationProvider) -> None:
        self.provider = provider
        self.translation = TranslationService(provider)
        self.grammar = GrammarService(provider)
        self.explanations = ExplanationService(provider)
        self.alternatives = AlternativesService(provider)
        self.transliteration = TransliterationService(provider)
        self.india_connect = IndiaConnectService(provider)

    async def run(self, request: AssistantRequest) -> AssistantResponse:
        if request.task == "translate":
            return await self._translate(request)
        if request.task == "india_connect":
            return await self._create_india_connect_message(request)
        if request.task == "grammar":
            source_language = await self._resolve_source(request.text, request.source_language)
            result = await self.grammar.correct(
                text=request.text,
                source_language=source_language,
            )
            return AssistantResponse(
                task="grammar",
                provider=self.provider.name,
                source_language=source_language,
                corrected_text=result.corrected_text,
                changes=result.changes,
            )
        if request.task == "explain":
            source_language = await self._resolve_source(request.text, request.source_language)
            result = await self.explanations.explain(
                text=request.text,
                source_language=source_language,
            )
            return AssistantResponse(
                task="explain",
                provider=self.provider.name,
                source_language=source_language,
                explanation=result.explanation,
            )
        if request.task == "transliterate":
            if request.target_script is None:
                raise TranslationError(
                    "Choose a target script for transliteration.",
                    status_code=422,
                    code="invalid_task_parameters",
                )
            result = await self.transliteration.transliterate(
                text=request.text,
                source_script=request.source_script,
                target_script=request.target_script,
            )
            return AssistantResponse(
                task="transliterate",
                provider=self.provider.name,
                source_language="hi",
                transliterated_text=result.transliterated_text,
                source_script=request.source_script,
                target_script=request.target_script,
                note=result.note or None,
            )
        raise TranslationError(
            "The selected assistant task is not supported.",
            status_code=422,
            code="unsupported_task",
        )

    async def _create_india_connect_message(
        self,
        request: AssistantRequest,
    ) -> AssistantResponse:
        if request.target_language is None:
            raise TranslationError(
                "Choose a target language for India Connect.",
                status_code=422,
                code="invalid_task_parameters",
            )
        source_language = await self._resolve_source(request.text, request.source_language)
        if (source_language, request.target_language) not in SUPPORTED_TRANSLATION_PAIRS:
            raise TranslationError(
                "The source and target languages must be different.",
                status_code=422,
                code="unsupported_language_pair",
            )
        result = await self.india_connect.create_message(
            intent=request.text,
            source_language=source_language,
            target_language=request.target_language,
            audience=request.audience,
        )
        return AssistantResponse(
            task="india_connect",
            provider=self.provider.name,
            source_language=source_language,
            target_language=request.target_language,
            translated_text=result.message,
            pronunciation_help=result.pronunciation_help,
            tone_guidance=result.tone_guidance,
        )

    async def _translate(self, request: AssistantRequest) -> AssistantResponse:
        if request.target_language is None:
            raise TranslationError(
                "A target language is required for translation.",
                status_code=422,
                code="invalid_task_parameters",
            )
        source_language, translated_text = await self.translation.translate_with_style(
            text=request.text,
            source_language=request.source_language,
            target_language=request.target_language,
            style=request.style,
        )
        alternatives = []
        if request.alternatives:
            alternatives = await self.alternatives.create(
                text=request.text,
                source_language=source_language,
                target_language=request.target_language,
                style=request.style,
                count=request.alternatives,
                primary_translation=translated_text,
            )
        explanation = None
        if request.include_explanation:
            explanation = (
                await self.explanations.explain(
                    text=request.text,
                    source_language=source_language,
                )
            ).explanation
        return AssistantResponse(
            task="translate",
            provider=self.provider.name,
            source_language=source_language,
            target_language=request.target_language,
            style=request.style,
            translated_text=translated_text,
            alternatives=alternatives,
            explanation=explanation,
        )

    async def _resolve_source(self, text: str, source_language: str) -> str:
        if source_language == "auto":
            return await self.translation.detect_source_language(text)
        return source_language

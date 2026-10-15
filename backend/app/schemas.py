from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.constants import (
    EXPERIMENTAL_LANGUAGES,
    MAX_TEXT_LENGTH,
    SUPPORTED_LANGUAGES,
    SUPPORTED_MODES,
    SUPPORTED_TRANSLATION_PAIRS,
)


class TranslationRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=MAX_TEXT_LENGTH)
    source_language: str
    target_language: str
    mode: Literal["simple", "advanced"]

    @field_validator("text")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Text cannot be empty.")
        return stripped

    @field_validator("source_language", "target_language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        code = value.strip().lower()
        if code == "auto":
            return code
        if code not in SUPPORTED_LANGUAGES:
            supported = ", ".join(sorted(SUPPORTED_LANGUAGES))
            raise ValueError(f"Unsupported language '{value}'. Supported languages: {supported}.")
        return code

    @field_validator("mode", mode="before")
    @classmethod
    def normalize_mode(cls, value: str) -> str:
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized not in SUPPORTED_MODES:
                raise ValueError("Mode must be 'simple' or 'advanced'.")
            return normalized
        return value

    @model_validator(mode="after")
    def languages_must_differ(self) -> "TranslationRequest":
        if self.target_language == "auto":
            raise ValueError("Target language must be selected explicitly.")
        if self.source_language != "auto" and self.source_language == self.target_language:
            raise ValueError("Source and target languages must be different.")
        if (
            self.source_language != "auto"
            and (self.source_language, self.target_language) not in SUPPORTED_TRANSLATION_PAIRS
        ):
            raise ValueError(
                "This source and target language combination is not currently available."
            )
        return self


TranslationStyle = Literal["natural", "formal", "casual", "literal"]
AssistantTask = Literal["translate", "grammar", "explain", "transliterate", "india_connect"]
IndiaConnectAudience = Literal[
    "general",
    "friend",
    "elder",
    "professional",
    "service_staff",
]


class AssistantRequest(BaseModel):
    task: AssistantTask
    text: str = Field(..., min_length=1, max_length=MAX_TEXT_LENGTH)
    source_language: str = "auto"
    target_language: str | None = None
    style: TranslationStyle = "natural"
    alternatives: int = Field(default=0, ge=0, le=3)
    include_explanation: bool = False
    source_script: Literal["auto", "latin", "devanagari"] = "auto"
    target_script: Literal["latin", "devanagari"] | None = None
    audience: IndiaConnectAudience = "general"

    @field_validator("text")
    @classmethod
    def normalize_assistant_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Text cannot be empty.")
        return stripped

    @field_validator("source_language")
    @classmethod
    def validate_assistant_source_language(cls, value: str) -> str:
        code = value.strip().lower()
        if code != "auto" and code not in SUPPORTED_LANGUAGES:
            raise ValueError(
                f"Unsupported language '{value}'. "
                f"Currently available: {', '.join(sorted(SUPPORTED_LANGUAGES))}."
            )
        return code

    @field_validator("target_language")
    @classmethod
    def validate_assistant_target_language(cls, value: str | None) -> str | None:
        if value is None:
            return value
        code = value.strip().lower()
        if code not in SUPPORTED_LANGUAGES:
            raise ValueError(
                f"Unsupported language '{value}'. "
                f"Currently available: {', '.join(sorted(SUPPORTED_LANGUAGES))}."
            )
        return code

    @model_validator(mode="after")
    def validate_task_parameters(self) -> "AssistantRequest":
        if self.task in {"translate", "india_connect"}:
            if self.target_language is None:
                raise ValueError("A target language is required for this task.")
            if self.source_language != "auto":
                if self.source_language == self.target_language:
                    raise ValueError("Source and target languages must be different.")
                if (self.source_language, self.target_language) not in SUPPORTED_TRANSLATION_PAIRS:
                    raise ValueError(
                        "This language pair is not currently available."
                    )
        elif self.alternatives or self.include_explanation:
            raise ValueError(
                "Alternatives and translation explanations are only available for translation."
            )
        if self.task == "india_connect" and (self.alternatives or self.include_explanation):
            raise ValueError("India Connect does not accept translation-only options.")

        if self.task != "india_connect" and self.audience != "general":
            raise ValueError("Audience options are only available for India Connect.")

        if self.task == "transliterate":
            if self.source_language != "hi" or self.target_script is None:
                raise ValueError(
                    "Transliteration currently requires Hindi and a target script."
                )
            if self.source_script != "auto" and self.source_script == self.target_script:
                raise ValueError("Source and target scripts must be different.")
        elif self.target_script is not None or self.source_script != "auto":
            raise ValueError("Script options are only available for transliteration.")
        return self


class AlternativeTranslation(BaseModel):
    text: str = Field(min_length=1)
    nuance: str = Field(min_length=1, max_length=240)


class AssistantResponse(BaseModel):
    task: AssistantTask
    provider: str
    source_language: str | None = None
    target_language: str | None = None
    style: TranslationStyle | None = None
    translated_text: str | None = None
    alternatives: list[AlternativeTranslation] = Field(default_factory=list, max_length=3)
    explanation: str | None = None
    corrected_text: str | None = None
    changes: str | None = None
    transliterated_text: str | None = None
    source_script: str | None = None
    target_script: str | None = None
    note: str | None = None
    pronunciation_help: str | None = None
    tone_guidance: str | None = None
    early_access: bool = False

    @model_validator(mode="after")
    def mark_early_access_languages(self) -> "AssistantResponse":
        self.early_access = any(
            language in EXPERIMENTAL_LANGUAGES
            for language in (self.source_language, self.target_language)
            if language is not None
        )
        return self


class TranslationResponse(BaseModel):
    translated_text: str
    source_language: str
    target_language: str
    mode: str
    provider: str
    early_access: bool = False

    @model_validator(mode="after")
    def mark_early_access_languages(self) -> "TranslationResponse":
        self.early_access = (
            self.source_language in EXPERIMENTAL_LANGUAGES
            or self.target_language in EXPERIMENTAL_LANGUAGES
        )
        return self


class ErrorResponse(BaseModel):
    error: str
    message: str


class HealthResponse(BaseModel):
    status: str
    provider: str
    model: str

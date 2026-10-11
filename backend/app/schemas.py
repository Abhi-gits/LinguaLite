from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.constants import (
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
        if self.source_language != "auto" and self.source_language == self.target_language:
            raise ValueError("Source and target languages must be different.")
        if (
            self.source_language != "auto"
            and (self.source_language, self.target_language) not in SUPPORTED_TRANSLATION_PAIRS
        ):
            raise ValueError(
                "This language pair is not currently supported. Supported pairs: "
                "English ↔ Hindi."
            )
        return self


TranslationStyle = Literal["natural", "formal", "casual", "literal"]
AssistantTask = Literal["translate", "grammar", "explain", "transliterate"]


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
        if self.task == "translate":
            if self.target_language is None:
                raise ValueError("A target language is required for translation.")
            if self.source_language != "auto":
                if self.source_language == self.target_language:
                    raise ValueError("Source and target languages must be different.")
                if (self.source_language, self.target_language) not in SUPPORTED_TRANSLATION_PAIRS:
                    raise ValueError(
                        "This language pair is not currently supported. "
                        "LinguaLite currently supports English ↔ Hindi."
                    )
        elif self.alternatives or self.include_explanation:
            raise ValueError(
                "Alternatives and translation explanations are only available for translation."
            )

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


class TranslationResponse(BaseModel):
    translated_text: str
    source_language: str
    target_language: str
    mode: str
    provider: str


class ErrorResponse(BaseModel):
    error: str
    message: str


class HealthResponse(BaseModel):
    status: str
    provider: str
    model: str

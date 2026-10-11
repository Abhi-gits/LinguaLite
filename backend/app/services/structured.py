import json
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.exceptions import TranslationError
from app.providers.base import TranslationProvider
from app.providers.prompts import extract_translation

ModelType = TypeVar("ModelType", bound=BaseModel)


async def generate_structured(
    provider: TranslationProvider,
    *,
    prompt: str,
    response_model: type[ModelType],
) -> ModelType:
    raw = await provider.generate(prompt=prompt, temperature=0.1)
    try:
        payload = json.loads(extract_translation(raw))
        return response_model.model_validate(payload)
    except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as exc:
        raise TranslationError(
            "The AI provider returned an unusable response. No result was invented.",
            status_code=502,
            code="malformed_response",
        ) from exc

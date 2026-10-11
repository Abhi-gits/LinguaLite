from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.config import Settings
from app.schemas import (
    AssistantRequest,
    AssistantResponse,
    ErrorResponse,
    HealthResponse,
    TranslationRequest,
    TranslationResponse,
)
from app.services.assistant import WritingAssistantService
from app.services.translation import TranslationService

router = APIRouter()


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_translation_service(request: Request) -> TranslationService:
    return request.app.state.translation_service


def get_assistant_service(request: Request) -> WritingAssistantService:
    return request.app.state.assistant_service


@router.get("/health", response_model=HealthResponse)
async def health(settings: Settings = Depends(get_app_settings)) -> HealthResponse:
    model = (
        settings.gemini_model
        if settings.translation_provider.strip().lower() == "gemini"
        else settings.ollama_model
    )
    return HealthResponse(
        status="ok",
        provider=settings.translation_provider,
        model=model,
    )


@router.post(
    "/translate",
    response_model=TranslationResponse,
    responses={
        400: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
        504: {"model": ErrorResponse},
    },
)
async def translate(
    payload: TranslationRequest,
    service: TranslationService = Depends(get_translation_service),
    settings: Settings = Depends(get_app_settings),
) -> TranslationResponse | JSONResponse:
    if len(payload.text) > settings.max_text_length:
        body = ErrorResponse(
            error="invalid_request",
            message=f"Text is too long. Use {settings.max_text_length} characters or fewer.",
        )
        return JSONResponse(status_code=422, content=body.model_dump())

    return await service.translate(payload)


@router.post(
    "/assist",
    response_model=AssistantResponse,
    responses={
        422: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
        504: {"model": ErrorResponse},
    },
)
async def assist(
    payload: AssistantRequest,
    service: WritingAssistantService = Depends(get_assistant_service),
    settings: Settings = Depends(get_app_settings),
) -> AssistantResponse | JSONResponse:
    if len(payload.text) > settings.max_text_length:
        body = ErrorResponse(
            error="invalid_request",
            message=f"Text is too long. Use {settings.max_text_length} characters or fewer.",
        )
        return JSONResponse(status_code=422, content=body.model_dump())
    return await service.run(payload)

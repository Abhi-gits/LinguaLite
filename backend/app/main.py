from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import logging

import httpx
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.config import Settings, get_settings
from app.exceptions import TranslationError
from app.providers import create_provider
from app.schemas import ErrorResponse
from app.services.assistant import WritingAssistantService
from app.services.translation import TranslationService

logger = logging.getLogger(__name__)


def _validation_message(exc: RequestValidationError) -> str:
    for error in exc.errors():
        loc = error.get("loc", ())
        msg = error.get("msg", "Invalid request.")
        if "text" in loc:
            if error.get("type") == "string_too_long":
                return "Text is too long. Shorten the input and try again."
            if error.get("type") in {"missing", "string_too_short", "value_error"}:
                return "Enter text to translate."
            return msg.removeprefix("Value error, ")
        if "source_language" in loc or "target_language" in loc:
            return msg.removeprefix("Value error, ")
        if "mode" in loc:
            return "Mode must be 'simple' or 'advanced'."
        if msg.startswith("Value error, "):
            return msg.removeprefix("Value error, ")
    return "Invalid translation request."


def create_app(
    settings: Settings | None = None,
    service: TranslationService | None = None,
) -> FastAPI:
    app_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if service is not None:
            app.state.translation_service = service
            app.state.assistant_service = WritingAssistantService(service.provider)
            yield
            return

        timeout = httpx.Timeout(app_settings.ollama_timeout_seconds, connect=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            provider = create_provider(app_settings, client)
            app.state.translation_service = TranslationService(provider)
            app.state.assistant_service = WritingAssistantService(provider)
            yield

    app = FastAPI(
        title=app_settings.app_name,
        description="Local AI-powered translator with a replaceable inference provider.",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.state.settings = app_settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origin_list(),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )
    app.include_router(router, prefix="/api")

    @app.exception_handler(TranslationError)
    async def translation_error_handler(_request: Request, exc: TranslationError) -> JSONResponse:
        body = ErrorResponse(error=exc.code, message=exc.message)
        return JSONResponse(status_code=exc.status_code, content=body.model_dump())

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        body = ErrorResponse(error="invalid_request", message=_validation_message(exc))
        return JSONResponse(status_code=422, content=body.model_dump())

    @app.exception_handler(Exception)
    async def unhandled_error_handler(_request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "Unhandled application error",
            exc_info=(type(exc), exc, exc.__traceback__),
        )
        body = ErrorResponse(
            error="internal_error",
            message="Translation could not be completed. Please try again.",
        )
        return JSONResponse(status_code=500, content=body.model_dump())

    return app


app = create_app()

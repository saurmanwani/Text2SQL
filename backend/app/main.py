import sys
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.llm import router as llm_router
from app.settings import Settings, get_settings


class HealthResponse(BaseModel):
    status: str
    version: str


class ErrorResponse(BaseModel):
    error: str
    detail: str
    code: str


def configure_logging(settings: Settings) -> None:
    logger.remove()
    logger.add(
        sys.stderr,
        level=settings.log_level.upper(),
        serialize=settings.app_env == "production",
    )


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)

    application = FastAPI(title=settings.app_name, version=settings.app_version)

    @application.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        _request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        detail = str(exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error="Request failed", detail=detail, code=f"http_{exc.status_code}"
            ).model_dump(),
        )

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                error="Validation failed", detail=str(exc), code="validation_error"
            ).model_dump(),
        )

    @application.middleware("http")
    async def unexpected_exception_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[JSONResponse]],
    ) -> JSONResponse:
        try:
            return await call_next(request)
        except Exception:
            logger.exception("Unhandled error while processing {}", request.url.path)
            return JSONResponse(
                status_code=500,
                content=ErrorResponse(
                    error="Internal server error",
                    detail="An unexpected error occurred.",
                    code="internal_error",
                ).model_dump(),
            )

    @application.get("/api/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(status="healthy", version=settings.app_version)

    application.include_router(llm_router)

    return application


app = create_app()

"""Aplicação REST da Judicial API (JUR-01).

Entrega apenas a fundação: app FastAPI, /health, middleware de correlation id,
logging estruturado e os handlers do contrato de erro unificado. Os endpoints de
pesquisa/tribunais/capabilities/retry serão adicionados nas próximas tasks.
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .config import get_settings
from .correlation import CorrelationIdMiddleware, get_correlation_id
from .enums import ErrorCode
from .errors import ErrorResponse, JudicialError
from .logging_config import configure_logging, get_logger
from .models import HealthResponse

settings = get_settings()
configure_logging(settings.log_level)
log = get_logger("app")


def create_app() -> FastAPI:
    app = FastAPI(title="Judicial API", version=settings.version)
    app.add_middleware(CorrelationIdMiddleware, header_name=settings.correlation_id_header)

    @app.exception_handler(JudicialError)
    async def _handle_judicial_error(request: Request, exc: JudicialError) -> JSONResponse:
        body = exc.to_response(correlation_id=get_correlation_id())
        log.warning(
            "erro de dominio",
            extra={"fields": {"code": exc.code.value, "http_status": exc.http_status}},
        )
        return JSONResponse(status_code=exc.http_status, content=body.model_dump(mode="json"))

    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        body = ErrorResponse(
            code=ErrorCode.BAD_REQUEST,
            message="Requisição inválida.",
            retryable=False,
            correlation_id=get_correlation_id(),
        )
        return JSONResponse(status_code=400, content=body.model_dump(mode="json"))

    @app.exception_handler(Exception)
    async def _handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        # Nunca expõe stack trace/detalhes internos ao consumidor (SPEC §23).
        body = ErrorResponse(
            code=ErrorCode.UNKNOWN_ERROR,
            message="Ocorreu um erro inesperado.",
            retryable=False,
            correlation_id=get_correlation_id(),
        )
        log.error("erro inesperado", exc_info=exc)
        return JSONResponse(status_code=500, content=body.model_dump(mode="json"))

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="UP", service=settings.service_name, version=settings.version)

    return app


app = create_app()

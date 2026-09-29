"""Aplicação REST da Judicial API.

Monta o app FastAPI completo (JUR-05): a fundação (health, correlation id,
logging estruturado, contrato de erro unificado) somada à camada de exposição —
endpoints REST de negócio, OpenAPI/Swagger customizado, autenticação por API key,
autorização por escopo, rate limiting, métricas, auditoria HTTP e hardening.

Ordem dos middlewares (de fora para dentro): correlation id → hardening/headers →
rate limit → auditoria. Assim o correlation id existe para todos os demais, o
hardening barra payloads abusivos cedo, o rate limit protege antes do trabalho, e
a auditoria registra o desfecho final de cada requisição.
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi

from .config import get_settings
from .correlation import CorrelationIdMiddleware, get_correlation_id
from .enums import ErrorCode
from .errors import ErrorResponse, JudicialError
from .logging_config import configure_logging, get_logger
from .metrics import get_metrics
from .models import HealthResponse
from .observability import RequestAuditMiddleware, SecurityHeadersMiddleware
from .ratelimit import RateLimitMiddleware, SlidingWindowLimiter
from .routes import router as judicial_router

settings = get_settings()
configure_logging(settings.log_level)
log = get_logger("app")

_API_DESCRIPTION = (
    "API unificada para pesquisa processual judicial nacional. O consumidor faz uma "
    "única requisição REST; a orquestração multi-tribunal (DataJud/CNJ), a "
    "normalização, os sinais jurídicos e a resiliência ficam encapsulados. "
    "Autenticação por API key no header configurado; escopos: `search` (disparar/"
    "reprocessar pesquisas) e `read` (consultar resultados e metadados)."
)


def _install_error_handlers(app: FastAPI) -> None:
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


def _install_middlewares(app: FastAPI) -> None:
    # A pilha é aplicada em ordem inversa de adição (o último add roda primeiro).
    # Adicionamos do mais interno para o mais externo para que o correlation id
    # envolva todos os outros.
    app.add_middleware(RequestAuditMiddleware)
    if settings.rate_limit_enabled:
        limiter = SlidingWindowLimiter(
            settings.rate_limit_requests, settings.rate_limit_window_seconds
        )
        app.add_middleware(
            RateLimitMiddleware, limiter=limiter, api_key_header=settings.api_key_header
        )
    app.add_middleware(SecurityHeadersMiddleware, max_request_bytes=settings.max_request_bytes)
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    app.add_middleware(CorrelationIdMiddleware, header_name=settings.correlation_id_header)


def _custom_openapi(app: FastAPI):
    def openapi():
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(
            title="Judicial API",
            version=settings.version,
            description=_API_DESCRIPTION,
            routes=app.routes,
        )
        # Esquema de segurança apiKey (documenta o header de autenticação).
        schema.setdefault("components", {}).setdefault("securitySchemes", {})[
            "ApiKeyAuth"
        ] = {
            "type": "apiKey",
            "in": "header",
            "name": settings.api_key_header,
            "description": "API key do consumidor. Escopos: search, read.",
        }
        # Aplica o esquema globalmente; /health e /metrics permanecem públicos.
        schema["security"] = [{"ApiKeyAuth": []}]
        app.openapi_schema = schema
        return schema

    return openapi


def create_app() -> FastAPI:
    app = FastAPI(
        title="Judicial API",
        version=settings.version,
        description=_API_DESCRIPTION,
        openapi_tags=[
            {"name": "judicial", "description": "Pesquisa processual multi-tribunal e metadados."},
            {"name": "infra", "description": "Saúde e observabilidade do serviço."},
        ],
    )

    _install_middlewares(app)
    _install_error_handlers(app)

    @app.get("/health", response_model=HealthResponse, tags=["infra"])
    def health() -> HealthResponse:
        return HealthResponse(status="UP", service=settings.service_name, version=settings.version)

    @app.get("/metrics", tags=["infra"])
    def metrics() -> dict:
        # Observabilidade mínima embutida (SPEC §72). Aberto por padrão (não expõe
        # dados sensíveis; apenas contadores agregados).
        return get_metrics().snapshot()

    app.include_router(judicial_router)
    app.openapi = _custom_openapi(app)
    return app


app = create_app()

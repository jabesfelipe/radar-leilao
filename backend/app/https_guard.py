"""Exigência de HTTPS (opcional) e HSTS.

Contexto (auditoria v1.0.2): a homologação em produção roda por IP público em HTTP, com portão
de cookie. Nesse modo, senha, token JWT (localStorage) e documentos trafegam sem criptografia.
Isso é aceitável só com dados fictícios. Antes de enviar um documento real (que contém CPF,
nomes e endereços) ou de ativar a OpenAI, o operador deve colocar HTTPS na frente e ligar
``REQUIRE_HTTPS=true``: a partir daí o backend recusa (426) qualquer requisição de API que não
chegue por HTTPS — a proteção deixa de depender de lembrar.

Como o esquema é detectado: o proxy reverso DEVE definir ``X-Forwarded-Proto`` (o nginx do
projeto faz ``proxy_set_header X-Forwarded-Proto $scheme``, sobrescrevendo qualquer valor do
cliente). Acesso direto de loopback (desenvolvimento local) é isento. ``/health`` é isento
(healthchecks internos do Docker usam HTTP).

Com HTTPS, a resposta recebe ``Strict-Transport-Security``.
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from .config import settings

_LOOPBACK = {"127.0.0.1", "::1", "localhost"}
HSTS_VALUE = "max-age=31536000; includeSubDomains"


def request_is_https(request: Request) -> bool:
    forwarded = request.headers.get("x-forwarded-proto", "")
    proto = (forwarded.split(",")[0].strip().lower() or request.url.scheme)
    return proto == "https"


class HttpsGuardMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        secure = request_is_https(request)
        if settings.require_https and not secure:
            client = request.client.host if request.client else ""
            if request.url.path != "/health" and client not in _LOOPBACK and request.method != "OPTIONS":
                return JSONResponse(
                    {"detail": "HTTPS obrigatório: acesse o Radar por uma conexão segura (https://)."},
                    status_code=426,
                )
        response = await call_next(request)
        if secure:
            response.headers.setdefault("Strict-Transport-Security", HSTS_VALUE)
        return response

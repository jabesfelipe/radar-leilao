"""Portão de segurança global da API (default-deny).

Antes desta camada, ~150 rotas (as de ``main.py`` e dos routers de hubs, jurídico,
débitos e mercado) não exigiam autenticação no backend: a única barreira era o cookie do
portão do proxy. Agora ``security_gate`` é registrada como dependência GLOBAL do app e:

1. libera apenas as rotas públicas estritamente necessárias (``/health`` e o login);
2. exige um portador autenticado (JWT de usuário ativo; ou o ``X-Admin-Token`` de
   compatibilidade, se configurado) em TODAS as demais — rotas novas nascem protegidas;
3. aplica autorização por permissão (RBAC existente em ``authz.py``): leitura para
   qualquer papel autenticado, escrita exige ``analysis:write`` e operações
   administrativas exigem ``admin:write``;
4. aplica rate limit e limite de concorrência às operações com potencial de consumo
   externo (LLM, embeddings, serviços externos) e a uploads.

As dependências por rota já existentes (``require_permission`` etc.) continuam valendo
como camada ADICIONAL. O cookie do proxy deixa de ser a única autorização de negócio.

Limites (rate limit / concorrência) são em memória e por processo: com N workers do
uvicorn o limite efetivo é até N vezes o configurado. Isso basta para conter abuso e
cliques repetidos; a proteção contra duplicidade entre processos usa locks do
PostgreSQL (ver ``locks.py``).
"""
from __future__ import annotations

import math
import re
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from . import auth as _auth
from .authz import PERM_ADMIN_WRITE, PERM_ANALYSIS_WRITE, PERM_READ, _role_from_admin_token, permissions_for
from .config import settings
from .database import get_db
from .logging_config import get_logger

log = get_logger("seguranca")

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


@dataclass(frozen=True)
class Policy:
    """Política de uma rota. ``permission=None`` significa rota pública."""
    permission: str | None
    bucket: str | None = None   # "critical" (LLM/externo) | "upload" | None
    label: str = ""


PUBLIC_ROUTES: frozenset[tuple[str, str]] = frozenset({
    ("GET", "/health"),
    ("POST", "/api/auth/login"),
})

_CRITICAL = Policy(PERM_ANALYSIS_WRITE, "critical", "operacao-critica")
_UPLOAD = Policy(PERM_ANALYSIS_WRITE, "upload", "upload")
_ADMIN = Policy(PERM_ADMIN_WRITE, None, "administrativa")

# (métodos, regex sobre o TEMPLATE da rota, política). Ordem importa (primeira vence).
_RULES: tuple[tuple[frozenset[str], re.Pattern[str], Policy], ...] = tuple(
    (frozenset(methods), re.compile(pattern), policy)
    for methods, pattern, policy in (
        # --- Operações com potencial de consumo externo (LLM/embeddings/serviços) ---
        ({"POST"}, r"^/api/imoveis/\{property_id\}/analisar$", _CRITICAL),
        ({"POST"}, r"^/api/imoveis/\{property_id\}/analises/\{analysis_id\}/agents/[a-z_]+$", _CRITICAL),
        ({"POST"}, r"^/api/imoveis/\{property_id\}/documentos/\{document_version_id\}/extrair$", _CRITICAL),
        ({"POST"}, r"^/api/imoveis/\{property_id\}/eventos/\{event_id\}/reanalisar$", _CRITICAL),
        ({"POST"}, r"^/api/monitoring/rag/reprocess$", _CRITICAL),
        ({"POST"}, r"^/api/imoveis/\{property_id\}/processos/consultar$", _CRITICAL),
        ({"POST"}, r"^/api/imoveis/\{property_id\}/debitos/consultar$", _CRITICAL),
        ({"POST"}, r"^/api/imoveis/\{property_id\}/localizacao/geocodificar$", _CRITICAL),
        # --- Upload de documentos (processa, indexa e pode gerar embeddings) ---
        ({"POST"}, r"^/api/imoveis/\{property_id\}/documentos$", _UPLOAD),
        ({"POST"}, r"^/api/documentos/\{document_id\}/versoes$", _UPLOAD),
        # --- Operações administrativas / credenciais ---
        ({"POST"}, r"^/api/checklist$", _ADMIN),
        ({"PATCH"}, r"^/api/checklist/\{item_id\}$", _ADMIN),
        ({"POST"}, r"^/api/checklist/\{item_id\}/(ativar|desativar)$", _ADMIN),
        ({"DELETE"}, r"^/api/leiloeiros/\{auctioneer_id\}$", _ADMIN),
        ({"POST", "PATCH", "DELETE"}, r"^/api/leiloeiros/\{auctioneer_id\}/portais(/\{portal_id\})?$", _ADMIN),
        ({"GET"}, r"^/api/leiloeiros/\{auctioneer_id\}/portais/\{portal_id\}/credencial$", _ADMIN),
    )
)


def classify(method: str, route_path: str) -> Policy:
    """Resolve a política de (método, template da rota). Default-deny."""
    method = method.upper()
    if (method, route_path) in PUBLIC_ROUTES:
        return Policy(None, None, "publica")
    for methods, pattern, policy in _RULES:
        if method in methods and pattern.match(route_path):
            return policy
    if method in SAFE_METHODS:
        return Policy(PERM_READ, None, "leitura")
    return Policy(PERM_ANALYSIS_WRITE, None, "escrita")


# ---------------------------------------------------------------------------
# Limites em memória (por processo)
# ---------------------------------------------------------------------------

class SlidingWindowLimiter:
    """Janela deslizante simples: no máximo ``limit`` eventos por ``window`` segundos."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key: str, limit: int, window: float = 60.0, now: float | None = None) -> float | None:
        """Registra um evento. Retorna ``None`` se permitido, ou os segundos até liberar."""
        now = time.monotonic() if now is None else now
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] >= window:
                q.popleft()
            if len(q) >= limit:
                return max(0.0, window - (now - q[0]))
            q.append(now)
            return None

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


class ConcurrencyGuard:
    """Limita operações críticas simultâneas por portador (cliques repetidos/abuso)."""

    def __init__(self) -> None:
        self._active: dict[str, int] = defaultdict(int)
        self._lock = threading.Lock()

    def acquire(self, key: str, maximum: int) -> bool:
        with self._lock:
            if self._active[key] >= maximum:
                return False
            self._active[key] += 1
            return True

    def release(self, key: str) -> None:
        with self._lock:
            if self._active.get(key, 0) > 0:
                self._active[key] -= 1
            if self._active.get(key) == 0:
                self._active.pop(key, None)

    def reset(self) -> None:
        with self._lock:
            self._active.clear()


LIMITER = SlidingWindowLimiter()
CONCURRENCY = ConcurrencyGuard()


def reset_limits() -> None:
    """Zera contadores (uso em testes)."""
    LIMITER.reset()
    CONCURRENCY.reset()


# ---------------------------------------------------------------------------
# Autenticação do portador
# ---------------------------------------------------------------------------

def _unauthorized() -> HTTPException:
    return HTTPException(401, "Autenticação necessária.", headers={"WWW-Authenticate": "Bearer"})


def authenticate_request(request: Request, db: Session) -> tuple[str, str]:
    """Retorna ``(papel, principal)``. Aceita JWT de usuário ativo (preferencial) ou o
    ``X-Admin-Token`` de compatibilidade (somente se configurado). Falha-fechada: 401."""
    user = _auth.get_optional_user(authorization=request.headers.get("authorization"), db=db)
    if user is not None:
        return user.role, f"user:{user.id}"
    role = _role_from_admin_token(request.headers.get("x-admin-token"))
    if role is not None:
        return role, f"token:{role}"
    raise _unauthorized()


def security_gate(request: Request, db: Session = Depends(get_db)):
    """Dependência global (``FastAPI(dependencies=[Depends(security_gate)])``)."""
    route = request.scope.get("route")
    template = getattr(route, "path", None) or request.url.path
    policy = classify(request.method, template)
    if policy.permission is None:
        yield
        return

    role, principal = authenticate_request(request, db)
    if policy.permission not in permissions_for(role):
        log.warning("acesso negado (permissao): principal=%s metodo=%s rota=%s exigida=%s", principal, request.method, template, policy.permission)
        raise HTTPException(403, "Você não tem permissão para executar esta operação.")
    request.state.principal = principal
    request.state.role = role

    held: str | None = None
    if policy.bucket:
        per_minute = settings.rate_limit_upload_per_minute if policy.bucket == "upload" else settings.rate_limit_critical_per_minute
        retry = LIMITER.hit(f"{principal}:{policy.bucket}", max(1, per_minute))
        if retry is not None:
            log.warning("rate limit: principal=%s bucket=%s rota=%s", principal, policy.bucket, template)
            raise HTTPException(429, "Muitas requisições para esta operação. Aguarde um instante e tente novamente.",
                                headers={"Retry-After": str(max(1, math.ceil(retry)))})
        if policy.bucket == "critical":
            if not CONCURRENCY.acquire(principal, max(1, settings.max_concurrent_critical_per_user)):
                log.warning("concorrencia: principal=%s rota=%s", principal, template)
                raise HTTPException(429, "Já existem operações em andamento para o seu usuário. Aguarde a conclusão.",
                                    headers={"Retry-After": "5"})
            held = principal
    try:
        yield
    finally:
        if held is not None:
            CONCURRENCY.release(held)

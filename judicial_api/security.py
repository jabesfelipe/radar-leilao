"""Segurança da Judicial API (JUR-05, SPEC §73).

Entrega os controles de acesso do CONSUMIDOR da API:

- autenticação por API key (header configurável);
- autorização por escopo (``search``, ``read``);
- mascaramento de dados sensíveis (CPF/CNPJ) para logs/auditoria (SPEC §71).

A credencial do DataJud (provider) é assunto separado (``config.datajud_api_key``);
aqui tratamos apenas de quem chama a Judicial API. Segredos nunca são logados nem
devolvidos em respostas (SPEC §23, §73).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from fastapi import Depends, Request

from .config import JudicialSettings, get_settings
from .enums import ErrorCode
from .errors import JudicialError

# Escopos reconhecidos. ``search`` autoriza disparar/reprocessar pesquisas
# (operações de escrita); ``read`` autoriza leitura de resultados/metadados.
SCOPE_SEARCH = "search"
SCOPE_READ = "read"


@dataclass(frozen=True)
class Principal:
    """Identidade autenticada do consumidor.

    ``key_id`` é um identificador NÃO-secreto e seguro para log/auditoria (os
    primeiros caracteres da chave); nunca a chave inteira. ``scopes`` vazio =
    acesso total (sem restrição de escopo).
    """

    key_id: str
    scopes: frozenset[str] = field(default_factory=frozenset)
    anonymous: bool = False

    def has_scope(self, scope: str) -> bool:
        # Conjunto vazio => sem restrição (acesso total). Anônimo (auth desligada)
        # também tem acesso total no modo local/dev.
        if self.anonymous or not self.scopes:
            return True
        return scope in self.scopes


def _safe_key_id(api_key: str) -> str:
    """Identificador não-secreto derivado da chave (para auditoria). Nunca expõe
    a chave completa."""
    prefix = api_key[:4]
    return f"key:{prefix}***" if prefix else "key:***"


def authenticate(request: Request, settings: JudicialSettings) -> Principal:
    """Resolve o Principal da requisição a partir do header de API key.

    - Auth desligada (nenhuma chave configurada e ``require_auth`` falso):
      devolve um Principal anônimo com acesso total (modo local/dev).
    - Auth ligada: exige header presente e chave válida, senão AUTHENTICATION_ERROR.
    """
    keys = settings.parsed_api_keys()
    if not settings.auth_enabled:
        return Principal(key_id="anonymous", scopes=frozenset(), anonymous=True)

    provided = request.headers.get(settings.api_key_header)
    provided = provided.strip() if provided else ""
    if not provided:
        raise JudicialError(
            ErrorCode.AUTHENTICATION_ERROR,
            "Credencial de acesso ausente.",
            http_status=401,
            retryable=False,
        )
    if provided not in keys:
        raise JudicialError(
            ErrorCode.AUTHENTICATION_ERROR,
            "Credencial de acesso inválida.",
            http_status=401,
            retryable=False,
        )
    return Principal(key_id=_safe_key_id(provided), scopes=keys[provided])


def get_principal(request: Request, settings: JudicialSettings = Depends(get_settings)) -> Principal:
    """Dependência do FastAPI: autentica e expõe o Principal atual."""
    principal = authenticate(request, settings)
    # Guarda no estado da requisição para a auditoria HTTP referenciar sem re-auth.
    request.state.principal = principal
    return principal


def require_scope(scope: str):
    """Fábrica de dependência que exige um escopo específico (autorização).

    Uso: ``principal: Principal = Depends(require_scope(SCOPE_SEARCH))``.
    """

    def _dependency(principal: Principal = Depends(get_principal)) -> Principal:
        if not principal.has_scope(scope):
            raise JudicialError(
                ErrorCode.AUTHORIZATION_ERROR,
                f"Acesso negado: o escopo '{scope}' é necessário para esta operação.",
                http_status=403,
                retryable=False,
            )
        return principal

    return _dependency


# ----------------------------------------------------------------------------
# Mascaramento de dados sensíveis (SPEC §71)
# ----------------------------------------------------------------------------
def mask_document(value: str | None) -> str | None:
    """Mascara CPF/CNPJ para uso em logs/auditoria, preservando apenas os últimos
    2 dígitos. Nunca registra o documento completo (SPEC §71)."""
    if not value:
        return value
    digits = "".join(ch for ch in value if ch.isdigit())
    if not digits:
        return "***"
    keep = digits[-2:] if len(digits) >= 2 else digits
    return f"***{keep}"


def masked_criteria(*, name: str | None = None, cpf: str | None = None, cnpj: str | None = None,
                    process_number: str | None = None) -> dict[str, str]:
    """Resumo NÃO-sensível dos critérios de uma pesquisa, para auditoria.

    Não inclui o nome completo nem documentos completos: apenas flags de presença
    e documentos mascarados (SPEC §71). O consumidor legítimo continua enviando os
    valores reais no corpo; o que evitamos é ESCREVÊ-LOS em log/auditoria.
    """
    summary: dict[str, str] = {}
    summary["has_name"] = "true" if name else "false"
    if cpf:
        summary["cpf"] = mask_document(cpf)
    if cnpj:
        summary["cnpj"] = mask_document(cnpj)
    if process_number:
        summary["has_process_number"] = "true"
    return summary

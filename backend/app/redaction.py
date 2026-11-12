"""Redação de segredos em textos (mensagens de erro, logs).

Módulo folha (sem imports da aplicação) para poder ser usado por ``logging_config``,
pelo gateway de LLM e pelos tratadores de erro sem ciclos de importação.

Cobre: chaves de API (``sk-...``), cabeçalhos ``Authorization``/``Bearer``, pares
``api_key=...``/``password=...``/``token=...``, connection strings de banco, JWTs e
valores de variáveis de ambiente sensíveis. É defesa em profundidade: o código também
evita colocar segredos em mensagens, mas bibliotecas de terceiros podem fazê-lo.
"""
from __future__ import annotations

import re

MAX_LEN = 2000

_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    # Connection strings (postgresql://user:senha@host/db, redis://..., etc.).
    (re.compile(r"(?i)\b[a-z][a-z0-9+.\-]{1,20}://[^\s'\"<>]*:[^\s'\"<>@]*@[^\s'\"<>]+"), "[REDACTED_URL]"),
    (re.compile(r"(?i)\b(postgres(?:ql)?(?:\+\w+)?|mysql|redis|amqp|mongodb)://[^\s'\"<>]+"), "[REDACTED_URL]"),
    # Authorization: Basic/Bearer xxx
    (re.compile(r"(?i)\b(authorization\s*[=:]\s*)(basic|bearer)?\s*[A-Za-z0-9._~+/=\-]+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=\-]+"), r"\1[REDACTED]"),
    # Pares chave=valor sensíveis (inclui OPENAI_API_KEY=..., PASSWORD=..., SECRET=...).
    (re.compile(r"(?i)((?:api[_\-]?key|secret(?:[_\-]?key)?|password|passwd|senha|token|x-admin-token|x-portal-admin-token)\s*[=:]\s*)[^\s,;&'\"]+"), r"\1[REDACTED]"),
    # Chaves OpenAI (sk-..., sk-proj-...) e variações comuns.
    (re.compile(r"\bsk-[A-Za-z0-9_\-*.]{3,}"), "[REDACTED]"),
    # JWT (três segmentos base64url começando com eyJ).
    (re.compile(r"\beyJ[A-Za-z0-9_\-]{5,}\.[A-Za-z0-9_\-]{5,}\.[A-Za-z0-9_\-]{5,}"), "[REDACTED_JWT]"),
)


def redact(text: str | None, *, max_len: int = MAX_LEN) -> str:
    """Remove segredos conhecidos do texto e o trunca em ``max_len`` caracteres."""
    if not text:
        return ""
    sanitized = str(text)[:max_len]
    for pattern, replacement in _PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized

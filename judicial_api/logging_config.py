"""Logging estruturado básico da Judicial API (JUR-01).

Emite logs em JSON de uma linha, sempre incluindo o correlation id da requisição
atual quando disponível. NUNCA registra segredos (API key, senha, token) nem
dados sensíveis completos (CPF/CNPJ integral) — isso é responsabilidade de quem
loga o conteúdo; aqui garantimos o formato e o correlation id (SPEC §71).
"""
from __future__ import annotations

import json
import logging
import os

from .correlation import get_correlation_id

_CONFIGURED = False
_NAMESPACE = "judicial"


class _JsonFormatter(logging.Formatter):
    """Formata cada registro como JSON de uma linha, com correlation id."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        correlation_id = get_correlation_id()
        if correlation_id:
            payload["correlation_id"] = correlation_id
        # Campos extras estruturados passados via logger.info(..., extra={"fields": {...}}).
        fields = getattr(record, "fields", None)
        if isinstance(fields, dict):
            payload.update(fields)
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str | None = None) -> None:
    """Configura o logging da Judicial API uma única vez (idempotente)."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    level_name = (level or os.getenv("JUDICIAL_LOG_LEVEL") or os.getenv("LOG_LEVEL") or "INFO").upper()
    resolved = getattr(logging, level_name, logging.INFO)

    handler = logging.StreamHandler()
    handler.setFormatter(_JsonFormatter())

    logger = logging.getLogger(_NAMESPACE)
    if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        logger.addHandler(handler)
    logger.setLevel(resolved)
    logger.propagate = False
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Retorna um logger sob o namespace 'judicial' (ex.: judicial.app)."""
    return logging.getLogger(f"{_NAMESPACE}.{name}")

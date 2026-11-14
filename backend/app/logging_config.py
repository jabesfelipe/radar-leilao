"""Configuração central de logging do Radar Leilão.

Objetivos (TASK 64):
- logs consultáveis para investigar cadastro, documentos, RAG, LangGraph, agentes e LLM;
- nunca registrar segredos (API keys, Authorization, senhas, tokens, credenciais).

O nível é controlado por LOG_LEVEL (DEBUG|INFO|WARNING|ERROR; padrão INFO).
Não registramos conteúdo integral de documentos — apenas metadados (ids, contagens,
status, durações).
"""
from __future__ import annotations

import logging
import os

_CONFIGURED = False

_LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] [%(correlation_id)s] %(message)s"
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"


class SecretRedactingFilter(logging.Filter):
    """Defesa em profundidade: redige segredos de QUALQUER mensagem de log (inclusive de
    bibliotecas) e anexa o ``correlation_id`` da requisição corrente.

    Também sanitiza a mensagem de exceção anexada (``exc_text``) quando o formatter a
    renderiza; o traceback permanece apenas no log interno, nunca na resposta HTTP.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        from .privacy import redact_pii
        from .redaction import redact
        from .request_context import get_correlation_id
        try:
            # Segredos + dados pessoais (CPF, e-mail, telefone...) nunca chegam ao log,
            # mesmo que uma biblioteca ou mensagem de erro os ecoe.
            record.msg = redact_pii(redact(record.getMessage(), max_len=4000), force=True)
            record.args = ()
            if record.exc_info and not record.exc_text:
                record.exc_text = redact_pii(redact(logging.Formatter().formatException(record.exc_info), max_len=8000), force=True)
        except Exception:  # nunca derrubar a aplicação por causa do filtro
            pass
        record.correlation_id = get_correlation_id()
        return True


def configure_logging() -> None:
    """Configura o logging da aplicação uma única vez (idempotente)."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
    handler.addFilter(SecretRedactingFilter())

    root = logging.getLogger()
    # Evita handlers duplicados quando o Uvicorn/reload reimporta o módulo.
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        root.addHandler(handler)
    root.setLevel(level)

    # Namespace da aplicação: sempre no nível configurado.
    logging.getLogger("radar").setLevel(level)
    # Clientes HTTP de terceiros registram em INFO a URL completa das chamadas externas (Geocoding leva
    # endereço e chave na query). Só avisos/erros desses loggers entram no log da aplicação.
    for noisy in ("httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(max(level, logging.WARNING))
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Retorna um logger sob o namespace 'radar' (ex.: radar.cadastro)."""
    return logging.getLogger(f"radar.{name}")

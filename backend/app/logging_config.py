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

_LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"


def configure_logging() -> None:
    """Configura o logging da aplicação uma única vez (idempotente)."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))

    root = logging.getLogger()
    # Evita handlers duplicados quando o Uvicorn/reload reimporta o módulo.
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        root.addHandler(handler)
    root.setLevel(level)

    # Namespace da aplicação: sempre no nível configurado.
    logging.getLogger("radar").setLevel(level)
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Retorna um logger sob o namespace 'radar' (ex.: radar.cadastro)."""
    return logging.getLogger(f"radar.{name}")

"""Abstração de armazenamento de documentos (Fase 4).

Objetivo: desacoplar o código do armazenamento físico para permitir trocar o backend
LOCAL (desenvolvimento) por S3/MinIO (produção) sem reescrever a aplicação. O MVP usa
``LocalStorage`` (comportamento atual, idêntico ao pipeline). A seleção é por
configuração (``settings.storage_backend``), nunca por hardcode.

NÃO cria buckets reais nem contrata serviços. O backend S3 só é instanciado quando
explicitamente configurado; sem ``boto3`` ou sem credenciais, falha de forma clara.
"""
from __future__ import annotations

from .base import DocumentStorage, StoredObject
from .local import LocalStorage


def build_storage(settings=None) -> DocumentStorage:
    """Fábrica do backend de storage a partir da configuração.

    - ``local`` (padrão): ``LocalStorage`` sobre ``settings.storage_dir``.
    - ``s3``/``minio``: ``S3Storage`` (import tardio; exige boto3 + config). Nunca cria
      bucket; apenas usa o que estiver configurado.
    """
    from ..config import settings as default_settings
    settings = settings or default_settings
    backend = (getattr(settings, "storage_backend", None) or "local").strip().lower()
    if backend in {"s3", "minio"}:
        from .s3 import S3Storage  # import tardio: só exige boto3 quando usado
        return S3Storage(settings)
    return LocalStorage(settings.storage_path)


__all__ = ["DocumentStorage", "StoredObject", "LocalStorage", "build_storage"]

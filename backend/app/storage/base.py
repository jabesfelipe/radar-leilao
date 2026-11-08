"""Contrato da abstração de storage de documentos (Fase 4)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class StoredObject:
    """Referência a um objeto persistido. ``uri`` é a forma canônica de localização
    (ex.: caminho local absoluto, ou ``s3://bucket/key``). ``key`` é o caminho lógico
    relativo (ex.: ``property-633/original/v1-edital.pdf``)."""
    key: str
    uri: str
    size: int | None = None


@runtime_checkable
class DocumentStorage(Protocol):
    """Interface mínima para persistir/ler/listar artefatos de documentos.

    Implementações: ``LocalStorage`` (filesystem) e ``S3Storage`` (S3/MinIO). O código
    da aplicação depende SOMENTE desta interface — trocar o backend não muda chamadas.
    """

    def write_bytes(self, key: str, data: bytes) -> StoredObject: ...

    def write_text(self, key: str, text: str, encoding: str = "utf-8") -> StoredObject: ...

    def read_bytes(self, key: str) -> bytes: ...

    def exists(self, key: str) -> bool: ...

    def uri_for(self, key: str) -> str: ...

    def backend_name(self) -> str: ...

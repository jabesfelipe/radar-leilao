"""Backend de storage LOCAL (filesystem). Comportamento idêntico ao pipeline atual."""
from __future__ import annotations

from pathlib import Path

from .base import DocumentStorage, StoredObject


class LocalStorage(DocumentStorage):
    """Persiste artefatos sob um diretório raiz (ex.: ``storage/documents``).

    As ``key`` são caminhos lógicos relativos (``property-633/original/v1-x.pdf``).
    Cria diretórios-pai sob demanda. Não segue symlinks para fora da raiz.
    """

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        # Normaliza e impede escapar da raiz (defesa contra path traversal).
        p = (self.root / key).resolve()
        root = self.root.resolve()
        if root not in p.parents and p != root:
            raise ValueError("Caminho de storage fora da raiz permitida")
        return p

    def write_bytes(self, key: str, data: bytes) -> StoredObject:
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return StoredObject(key=key, uri=str(p), size=len(data))

    def write_text(self, key: str, text: str, encoding: str = "utf-8") -> StoredObject:
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding=encoding)
        return StoredObject(key=key, uri=str(p), size=len(text.encode(encoding)))

    def read_bytes(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def exists(self, key: str) -> bool:
        return self._path(key).exists()

    def uri_for(self, key: str) -> str:
        return str(self._path(key))

    def backend_name(self) -> str:
        return "local"

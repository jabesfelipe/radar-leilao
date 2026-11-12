"""Validação de uploads de documentos.

Camadas (todas no backend; o limite do nginx é só a primeira barreira):
- leitura em partes com teto de tamanho (413 sem carregar o arquivo inteiro na memória
  além do limite) e rejeição de arquivo vazio;
- nome de arquivo seguro (sem caminho, sem caracteres de controle, tamanho limitado);
- extensão permitida;
- MIME declarado coerente com a extensão (ou genérico);
- assinatura real do conteúdo ("magic bytes") coerente com a extensão — um ``.pdf`` que
  não começa com ``%PDF-`` é recusado; DOCX/XLSX são validados como ZIP com a estrutura
  OOXML esperada e com teto de descompressão (zip bomb);
- arquivos de texto não podem conter bytes nulos.

As mensagens devolvidas ao usuário são fixas e não ecoam conteúdo do arquivo.
"""
from __future__ import annotations

import io
import re
import unicodedata
import zipfile
from pathlib import PurePosixPath

from fastapi import HTTPException, UploadFile

from .config import settings

ALLOWED_EXTENSIONS = frozenset({".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".txt", ".md", ".png", ".jpg", ".jpeg"})

_GENERIC_MIME = frozenset({"", "application/octet-stream", "binary/octet-stream"})

_MIME_BY_EXT: dict[str, frozenset[str]] = {
    ".pdf": frozenset({"application/pdf", "application/x-pdf"}),
    ".doc": frozenset({"application/msword"}),
    ".docx": frozenset({"application/vnd.openxmlformats-officedocument.wordprocessingml.document"}),
    ".xls": frozenset({"application/vnd.ms-excel"}),
    ".xlsx": frozenset({"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}),
    ".csv": frozenset({"text/csv", "application/csv", "application/vnd.ms-excel", "text/plain"}),
    ".txt": frozenset({"text/plain"}),
    ".md": frozenset({"text/markdown", "text/x-markdown", "text/plain"}),
    ".png": frozenset({"image/png"}),
    ".jpg": frozenset({"image/jpeg", "image/jpg"}),
    ".jpeg": frozenset({"image/jpeg", "image/jpg"}),
}

_OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_MAX_FILENAME = 150
_MAX_UNCOMPRESSED = 300 * 1024 * 1024  # teto de descompressão de DOCX/XLSX
_CHUNK = 1024 * 1024


def max_upload_bytes() -> int:
    return max(1, int(settings.upload_max_mb)) * 1024 * 1024


def sanitize_filename(filename: str | None) -> str:
    """Nome seguro para exibição/armazenamento. Levanta ``ValueError`` se inválido.

    Remove qualquer componente de diretório (inclusive ``..\\`` estilo Windows), caracteres
    de controle e símbolos fora de ``[\\w.-() ]``; limita o comprimento preservando a
    extensão. A extensão final precisa estar na lista permitida.
    """
    raw = filename or "documento"
    if "\x00" in raw:
        raise ValueError("Nome de arquivo inválido")
    name = PurePosixPath(raw.replace("\\", "/")).name.strip()
    name = unicodedata.normalize("NFC", name)
    name = "".join(ch for ch in name if unicodedata.category(ch)[0] != "C")
    name = re.sub(r"[^\w.\-() ]", "_", name)
    name = re.sub(r"\s+", " ", name).strip().lstrip(".")
    if not name or name in {".", ".."}:
        raise ValueError("Nome de arquivo inválido")
    suffix = PurePosixPath(name).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError("Extensão de documento não permitida")
    if len(name) > _MAX_FILENAME:
        stem = PurePosixPath(name).stem[: _MAX_FILENAME - len(suffix)]
        name = f"{stem}{suffix}"
    return name


async def read_limited(file: UploadFile, max_bytes: int | None = None) -> bytes:
    """Lê o upload em partes e recusa (413) assim que ultrapassa o limite."""
    limit = max_bytes or max_upload_bytes()
    parts: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(_CHUNK)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise HTTPException(413, f"Arquivo acima do limite de {limit // (1024 * 1024)} MB.")
        parts.append(chunk)
    return b"".join(parts)


def _bad(message: str, status: int = 400) -> HTTPException:
    return HTTPException(status, message)


def _check_ooxml(content: bytes, prefix: str) -> None:
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            names = zf.namelist()
            if "[Content_Types].xml" not in names or not any(n.startswith(prefix) for n in names):
                raise _bad("O conteúdo do arquivo não corresponde à extensão informada.")
            if sum(info.file_size for info in zf.infolist()) > _MAX_UNCOMPRESSED:
                raise _bad("Arquivo rejeitado: conteúdo descompactado excede o limite permitido.")
    except zipfile.BadZipFile as exc:
        raise _bad("Arquivo corrompido ou em formato inválido.") from exc


def validate_upload(filename: str | None, content_type: str | None, content: bytes, max_bytes: int | None = None) -> str:
    """Valida o upload e devolve o nome seguro. Levanta ``HTTPException`` (400/413/415)."""
    limit = max_bytes or max_upload_bytes()
    try:
        safe_name = sanitize_filename(filename)
    except ValueError as exc:
        raise _bad(str(exc)) from exc
    if not content:
        raise _bad("O arquivo enviado está vazio.")
    if len(content) > limit:
        raise _bad(f"Arquivo acima do limite de {limit // (1024 * 1024)} MB.", 413)

    ext = PurePosixPath(safe_name).suffix.lower()
    declared = (content_type or "").split(";")[0].strip().lower()
    if declared not in _GENERIC_MIME and declared not in _MIME_BY_EXT[ext]:
        raise _bad("Tipo de arquivo (MIME) incompatível com a extensão informada.", 415)

    head = content[:1024]
    if ext == ".pdf":
        if b"%PDF-" not in head:
            raise _bad("O conteúdo do arquivo não corresponde à extensão informada (PDF inválido).")
    elif ext == ".png":
        if not content.startswith(b"\x89PNG\r\n\x1a\n"):
            raise _bad("O conteúdo do arquivo não corresponde à extensão informada (PNG inválido).")
    elif ext in {".jpg", ".jpeg"}:
        if not content.startswith(b"\xff\xd8\xff"):
            raise _bad("O conteúdo do arquivo não corresponde à extensão informada (JPEG inválido).")
    elif ext in {".doc", ".xls"}:
        if not content.startswith(_OLE_MAGIC):
            raise _bad("O conteúdo do arquivo não corresponde à extensão informada.")
    elif ext == ".docx":
        _check_ooxml(content, "word/")
    elif ext == ".xlsx":
        _check_ooxml(content, "xl/")
    else:  # .txt, .md, .csv
        if b"\x00" in content[:65536]:
            raise _bad("O conteúdo do arquivo não é um texto válido.")
    return safe_name

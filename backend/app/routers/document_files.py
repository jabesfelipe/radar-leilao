"""Download/visualização de arquivos de documentos (Fase hospedagem).

Documentos NUNCA são servidos por URL pública/estática: todo acesso passa por esta
rota, que exige usuário autenticado e resolve o arquivo pela abstração de storage.
Só serve arquivos que estejam DENTRO da raiz de storage configurada (guard contra
path traversal e contra caminhos absolutos legados fora do volume).
"""
from __future__ import annotations

import mimetypes
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from .. import models
from ..auth import get_current_user
from ..config import settings
from ..database import get_db
from ..storage import build_storage

router = APIRouter(prefix="/api/documentos", tags=["documentos"])


def _local_key(uri: str) -> str | None:
    """Chave relativa à raiz do storage local; None se o caminho estiver fora dela."""
    try:
        root = settings.storage_path.resolve()
        rel = Path(uri).resolve().relative_to(root)
        return rel.as_posix()
    except (ValueError, OSError):
        return None


def _s3_key(uri: str) -> str | None:
    bucket = settings.storage_s3_bucket or ""
    prefix = (settings.storage_s3_prefix or "").strip("/")
    head = f"s3://{bucket}/"
    if not uri.startswith(head):
        return None
    key = uri[len(head):]
    if prefix and key.startswith(prefix + "/"):
        key = key[len(prefix) + 1:]
    return key


@router.get("/versoes/{version_id}/arquivo")
def download_version_file(
    version_id: int,
    variante: str = "original",
    db: Session = Depends(get_db),
    _user: models.User = Depends(get_current_user),
):
    """Baixa o arquivo ORIGINAL (padrão) ou o texto NORMALIZADO (variante=normalizado)."""
    version = db.get(models.DocumentVersion, version_id)
    if version is None:
        raise HTTPException(404, "Versão de documento não encontrada")
    if variante not in {"original", "normalizado"}:
        raise HTTPException(422, "variante inválida (original|normalizado)")
    uri = version.original_path if variante == "original" else version.normalized_path
    if not uri:
        raise HTTPException(404, "Arquivo indisponível para esta variante")

    storage = build_storage(settings)
    name = Path(uri.split("://", 1)[-1]).name
    media = mimetypes.guess_type(name)[0] or "application/octet-stream"
    headers = {"Content-Disposition": f'attachment; filename="{name}"', "X-Content-Type-Options": "nosniff"}

    if storage.backend_name() == "local":
        key = _local_key(uri)
        if key is None or not storage.exists(key):
            raise HTTPException(404, "Arquivo não encontrado no storage")
        return FileResponse(storage.uri_for(key), media_type=media, headers=headers)

    key = _s3_key(uri)
    if key is None or not storage.exists(key):
        raise HTTPException(404, "Arquivo não encontrado no storage")
    return Response(content=storage.read_bytes(key), media_type=media, headers=headers)

import hashlib
import json
import tempfile
from pathlib import Path
from sqlalchemy.orm import Session
from .. import models
from ..config import settings
from ..logging_config import get_logger
from ..storage import build_storage
from .normalizer import DocumentNormalizer
from .categories import chunk_category_metadata
from .chunker import chunk_markdown
from .embedding import embed_pending_chunks
from .readiness import blocking_state
from . import dedup, states

log = get_logger("documentos")

ALLOWED_DOCUMENT_EXTENSIONS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".txt", ".md", ".png", ".jpg", ".jpeg"}


def safe_filename(filename: str) -> str:
    """Nome seguro (sem caminho/controle, comprimento limitado, extensão permitida).
    Fonte única da regra: ``upload_security.sanitize_filename`` (levanta ValueError)."""
    from ..upload_security import sanitize_filename
    return sanitize_filename(filename)


class DocumentPipeline:
    def __init__(self, db: Session): self.db = db

    def ingest(self, document: models.Document, content: bytes, filename: str, *, dedup_reuse: bool = True, opportunity_id: int | None = None) -> models.DocumentVersion:
        filename = safe_filename(filename)
        digest = dedup.content_digest(content)

        # Dedup por conteúdo (Fase 2): se o upload é byte-idêntico a uma versão já
        # processada DESTE documento, reaproveitamos — não recriamos chunks/embeddings
        # nem reescrevemos o arquivo. Preserva as relações do documento (imóvel/origem).
        if dedup_reuse:
            reusable = dedup.find_reusable_version(document, digest)
            if reusable is not None:
                document.status = states.CONCLUIDO
                self.db.flush()
                log.info(
                    "documento reaproveitado (conteudo identico): document_id=%s version_reutilizada=%s hash=%s",
                    document.id, getattr(reusable, "version", "?"), digest[:12],
                )
                return reusable

        document.status = states.PROCESSANDO_EMBEDDING
        version = None
        try:
            storage = build_storage(settings)
            version_number = dedup.next_version_number(document)
            stem = Path(filename).stem
            base_key = f"property-{document.property_id}"
            original_key = f"{base_key}/original/v{version_number}-{filename}"
            normalized_key = f"{base_key}/normalized/v{version_number}-{stem}.md"
            metadata_key = f"{base_key}/metadata/v{version_number}-{stem}.json"

            # Persiste o arquivo original pela abstração de storage (local/S3/MinIO).
            original_obj = storage.write_bytes(original_key, content)

            # O normalizador exige um caminho local legível. Com backend local, usamos
            # o próprio arquivo; com backend remoto, materializamos um temporário.
            if storage.backend_name() == "local":
                local_original = Path(original_obj.uri)
                tmp_cleanup: Path | None = None
            else:
                suffix = Path(filename).suffix
                fd, tmp_name = tempfile.mkstemp(suffix=suffix)
                tmp_path = Path(tmp_name)
                import os as _os
                with _os.fdopen(fd, "wb") as fh:
                    fh.write(content)
                local_original = tmp_path
                tmp_cleanup = tmp_path

            log.info("normalizacao iniciada: document_id=%s version=%s tipo=%s", document.id, version_number, document.document_type)
            try:
                normalized, extraction = DocumentNormalizer().normalize(local_original, document.document_type)
            finally:
                if tmp_cleanup is not None:
                    try:
                        tmp_cleanup.unlink(missing_ok=True)  # limpa o temporário de processamento
                    except OSError:
                        pass
            log.info("normalizacao concluida: document_id=%s version=%s markdown_chars=%d", document.id, version_number, len(normalized or ""))

            normalized_obj = storage.write_text(normalized_key, normalized)
            storage.write_text(metadata_key, json.dumps(extraction, ensure_ascii=False, indent=2))
            version = models.DocumentVersion(document_id=document.id, version=version_number, content_hash=digest, original_path=original_obj.uri, normalized_path=normalized_obj.uri, normalized_markdown=normalized, extraction_metadata=extraction, status=states.AGUARDANDO_EMBEDDING)
            self.db.add(version); self.db.flush()
            chunk_count = 0
            for chunk in chunk_markdown(normalized, extraction):
                metadata = {**extraction, **chunk.metadata, "property_id": document.property_id, "document_id": document.id, "document_version_id": version.id, "document_type": document.document_type, "source": document.source, "chunk_index": chunk.index, **chunk_category_metadata(document.document_type)}
                if opportunity_id is not None:
                    metadata["opportunity_id"] = opportunity_id
                self.db.add(models.DocumentChunk(document_version_id=version.id, chunk_index=chunk.index, content=chunk.content, page=chunk.metadata.get("page"), section=chunk.metadata.get("section") or chunk.metadata.get("subsection"), metadata_json=metadata))
                chunk_count += 1
            self.db.flush()
            # Gera/persiste o embedding dos chunks recém-criados quando houver
            # provider/chave. Falha de embedding NÃO quebra a ingestão (o helper
            # captura erros e retorna telemetria); sem chave, apenas segue por texto.
            telemetry: dict = {}
            # Sem texto utilizável (arquivo vazio, PDF escaneado sem OCR, OCR que falhou): o
            # documento NÃO é apresentado como processado, não gera embeddings (sem custo
            # inútil) e seus chunks ficam fora do RAG (ver retriever/worker).
            blocking = blocking_state(extraction, chunk_count)
            if blocking is not None:
                version.status = blocking
                document.status = blocking
                self.db.flush()
                log.warning("documento sem texto utilizavel: document_id=%s version=%s estado=%s chars=%s", document.id, version_number, blocking, extraction.get("char_count"))
                return version
            try:
                version.status = states.PROCESSANDO_EMBEDDING
                telemetry = embed_pending_chunks(self.db, version.id) or {}
            except Exception:  # defesa extra: nunca deixar o embedding abortar a ingestão
                log.warning("embedding de chunks ignorado por erro inesperado: document_id=%s version=%s", document.id, version_number)
            # Estado terminal explícito: INDEXADO SOMENTE quando TODOS os chunks têm vetor;
            # CONCLUIDO (texto pronto, sem vetores completos) caso contrário. Antes, um único
            # vetor persistido bastava para marcar INDEXADO.
            persisted = int(telemetry.get("embeddings_persistidos") or 0)
            version.status = states.INDEXADO if (chunk_count > 0 and persisted >= chunk_count) else states.CONCLUIDO
            document.status = states.CONCLUIDO
            self.db.flush()
            log.info("documento processado: document_id=%s version=%s chunks=%d hash=%s estado=%s", document.id, version_number, chunk_count, digest[:12], version.status)
            return version
        except Exception as exc:
            document.status = states.ERRO
            if version is not None: version.status = states.ERRO
            self.db.flush()
            log.exception("falha no pipeline de documento: document_id=%s tipo_erro=%s", document.id, type(exc).__name__)
            raise
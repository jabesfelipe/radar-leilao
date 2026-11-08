import hashlib
import json
from pathlib import Path
from sqlalchemy.orm import Session
from .. import models
from ..config import settings
from ..logging_config import get_logger
from .normalizer import DocumentNormalizer
from .chunker import chunk_markdown
from .embedding import embed_pending_chunks
from . import dedup, states

log = get_logger("documentos")

ALLOWED_DOCUMENT_EXTENSIONS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".txt", ".md", ".png", ".jpg", ".jpeg"}


def safe_filename(filename: str) -> str:
    name = Path(filename or "documento").name
    if not name or name in {".", ".."} or Path(name).suffix.lower() not in ALLOWED_DOCUMENT_EXTENSIONS:
        raise ValueError("Extensão de documento não permitida")
    return name


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
            property_dir = settings.storage_path / f"property-{document.property_id}"
            original_dir, normalized_dir, metadata_dir = (property_dir / name for name in ("original", "normalized", "metadata"))
            for path in (original_dir, normalized_dir, metadata_dir): path.mkdir(parents=True, exist_ok=True)
            version_number = dedup.next_version_number(document)
            original_path = original_dir / f"v{version_number}-{filename}"
            original_path.write_bytes(content)
            log.info("normalizacao iniciada: document_id=%s version=%s tipo=%s", document.id, version_number, document.document_type)
            normalized, extraction = DocumentNormalizer().normalize(original_path, document.document_type)
            log.info("normalizacao concluida: document_id=%s version=%s markdown_chars=%d", document.id, version_number, len(normalized or ""))
            normalized_path = normalized_dir / f"v{version_number}-{Path(filename).stem}.md"
            normalized_path.write_text(normalized, encoding="utf-8")
            (metadata_dir / f"v{version_number}-{Path(filename).stem}.json").write_text(json.dumps(extraction, ensure_ascii=False, indent=2), encoding="utf-8")
            version = models.DocumentVersion(document_id=document.id, version=version_number, content_hash=digest, original_path=str(original_path), normalized_path=str(normalized_path), normalized_markdown=normalized, extraction_metadata=extraction, status=states.AGUARDANDO_EMBEDDING)
            self.db.add(version); self.db.flush()
            chunk_count = 0
            for chunk in chunk_markdown(normalized, extraction):
                metadata = {**extraction, **chunk.metadata, "property_id": document.property_id, "document_id": document.id, "document_version_id": version.id, "document_type": document.document_type, "source": document.source, "chunk_index": chunk.index}
                if opportunity_id is not None:
                    metadata["opportunity_id"] = opportunity_id
                self.db.add(models.DocumentChunk(document_version_id=version.id, chunk_index=chunk.index, content=chunk.content, page=chunk.metadata.get("page"), section=chunk.metadata.get("section") or chunk.metadata.get("subsection"), metadata_json=metadata))
                chunk_count += 1
            self.db.flush()
            # Gera/persiste o embedding dos chunks recém-criados quando houver
            # provider/chave. Falha de embedding NÃO quebra a ingestão (o helper
            # captura erros e retorna telemetria); sem chave, apenas segue por texto.
            telemetry: dict = {}
            try:
                version.status = states.PROCESSANDO_EMBEDDING
                telemetry = embed_pending_chunks(self.db, version.id) or {}
            except Exception:  # defesa extra: nunca deixar o embedding abortar a ingestão
                log.warning("embedding de chunks ignorado por erro inesperado: document_id=%s version=%s", document.id, version_number)
            # Estado terminal explícito: INDEXADO quando houve vetor; CONCLUIDO caso
            # contrário (ingestão por texto, sem chave/provider). Nunca "meio-termo".
            indexed = bool(telemetry.get("embeddings_persistidos"))
            version.status = states.INDEXADO if indexed else states.CONCLUIDO
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
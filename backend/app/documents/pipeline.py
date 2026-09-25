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

log = get_logger("documentos")

ALLOWED_DOCUMENT_EXTENSIONS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".txt", ".md", ".png", ".jpg", ".jpeg"}


def safe_filename(filename: str) -> str:
    name = Path(filename or "documento").name
    if not name or name in {".", ".."} or Path(name).suffix.lower() not in ALLOWED_DOCUMENT_EXTENSIONS:
        raise ValueError("Extensão de documento não permitida")
    return name


class DocumentPipeline:
    def __init__(self, db: Session): self.db = db

    def ingest(self, document: models.Document, content: bytes, filename: str) -> models.DocumentVersion:
        filename = safe_filename(filename)
        document.status = "PROCESSANDO"
        version = None
        try:
            property_dir = settings.storage_path / f"property-{document.property_id}"
            original_dir, normalized_dir, metadata_dir = (property_dir / name for name in ("original", "normalized", "metadata"))
            for path in (original_dir, normalized_dir, metadata_dir): path.mkdir(parents=True, exist_ok=True)
            digest = hashlib.sha256(content).hexdigest()
            version_number = max((item.version for item in document.versions), default=0) + 1
            original_path = original_dir / f"v{version_number}-{filename}"
            original_path.write_bytes(content)
            log.info("normalizacao iniciada: document_id=%s version=%s tipo=%s", document.id, version_number, document.document_type)
            normalized, extraction = DocumentNormalizer().normalize(original_path, document.document_type)
            log.info("normalizacao concluida: document_id=%s version=%s markdown_chars=%d", document.id, version_number, len(normalized or ""))
            normalized_path = normalized_dir / f"v{version_number}-{Path(filename).stem}.md"
            normalized_path.write_text(normalized, encoding="utf-8")
            (metadata_dir / f"v{version_number}-{Path(filename).stem}.json").write_text(json.dumps(extraction, ensure_ascii=False, indent=2), encoding="utf-8")
            version = models.DocumentVersion(document_id=document.id, version=version_number, content_hash=digest, original_path=str(original_path), normalized_path=str(normalized_path), normalized_markdown=normalized, extraction_metadata=extraction, status="PROCESSANDO")
            self.db.add(version); self.db.flush()
            chunk_count = 0
            for chunk in chunk_markdown(normalized, extraction):
                metadata = {**extraction, **chunk.metadata, "property_id": document.property_id, "document_id": document.id, "document_version_id": version.id, "document_type": document.document_type, "source": document.source, "chunk_index": chunk.index}
                self.db.add(models.DocumentChunk(document_version_id=version.id, chunk_index=chunk.index, content=chunk.content, page=chunk.metadata.get("page"), section=chunk.metadata.get("section") or chunk.metadata.get("subsection"), metadata_json=metadata))
                chunk_count += 1
            version.status = "PROCESSADO"
            document.status = "PROCESSADO"
            self.db.flush()
            # Gera/persiste o embedding dos chunks recém-criados quando houver
            # provider/chave. Falha de embedding NÃO quebra a ingestão (o helper
            # captura erros e retorna telemetria); sem chave, apenas segue por texto.
            try:
                embed_pending_chunks(self.db, version.id)
            except Exception:  # defesa extra: nunca deixar o embedding abortar a ingestão
                log.warning("embedding de chunks ignorado por erro inesperado: document_id=%s version=%s", document.id, version_number)
            log.info("documento processado: document_id=%s version=%s chunks=%d hash=%s", document.id, version_number, chunk_count, digest[:12])
            return version
        except Exception as exc:
            document.status = "ERRO"
            if version is not None: version.status = "ERRO"
            self.db.flush()
            log.exception("falha no pipeline de documento: document_id=%s tipo_erro=%s", document.id, type(exc).__name__)
            raise
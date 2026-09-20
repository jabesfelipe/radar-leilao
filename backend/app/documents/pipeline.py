import hashlib
import json
from pathlib import Path
from sqlalchemy.orm import Session
from .. import models
from ..config import settings
from .normalizer import DocumentNormalizer
from .chunker import chunk_markdown

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
        property_dir = settings.storage_path / f"property-{document.property_id}"
        original_dir, normalized_dir, metadata_dir = (property_dir / name for name in ("original", "normalized", "metadata"))
        for path in (original_dir, normalized_dir, metadata_dir): path.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(content).hexdigest()
        version_number = max((version.version for version in document.versions), default=0) + 1
        original_path = original_dir / f"v{version_number}-{filename}"
        original_path.write_bytes(content)
        normalized, extraction = DocumentNormalizer().normalize(original_path, document.document_type)
        normalized_path = normalized_dir / f"v{version_number}-{Path(filename).stem}.md"
        normalized_path.write_text(normalized, encoding="utf-8")
        (metadata_dir / f"v{version_number}-{Path(filename).stem}.json").write_text(json.dumps(extraction, ensure_ascii=False, indent=2), encoding="utf-8")
        version = models.DocumentVersion(document_id=document.id, version=version_number, content_hash=digest, original_path=str(original_path), normalized_path=str(normalized_path), normalized_markdown=normalized, extraction_metadata=extraction, status="PROCESSADO")
        self.db.add(version); self.db.flush()
        for chunk in chunk_markdown(normalized, extraction):
            self.db.add(models.DocumentChunk(document_version_id=version.id, chunk_index=chunk.index, content=chunk.content, page=chunk.metadata.get("page"), section=chunk.metadata.get("section"), metadata_json=chunk.metadata))
        document.status = "PROCESSADO"
        self.db.flush()
        return version

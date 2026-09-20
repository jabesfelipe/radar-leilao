from pathlib import Path
from typing import Any


class DocumentNormalizer:
    """Normaliza formatos suportados sem substituir o original armazenado."""

    def normalize(self, original_path: Path, document_type: str) -> tuple[str, dict[str, Any]]:
        metadata: dict[str, Any] = {"engine": "MarkItDown", "document_type": document_type}
        try:
            from markitdown import MarkItDown
            result = MarkItDown().convert(str(original_path))
            metadata.update({"title": getattr(result, "title", None), "ocr": False})
            return result.text_content, metadata
        except Exception as exc:
            if original_path.suffix.lower() in {".txt", ".md", ".csv"}:
                metadata.update({"engine": "texto-direto", "fallback_reason": str(exc), "ocr": False})
                return original_path.read_text(encoding="utf-8", errors="replace"), metadata
            raise RuntimeError(f"Não foi possível normalizar o documento com MarkItDown: {exc}") from exc

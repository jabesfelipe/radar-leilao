from pathlib import Path
from typing import Any

from ..config import settings
from ..logging_config import get_logger
from .ocr import ocr_available, run_ocr

log = get_logger("normalizer")

# Extensões binárias cuja extração textual pode falhar silenciosamente
# (ex.: PDF escaneado sem camada de texto, imagem). Para elas a detecção de
# extração insuficiente é relevante e o OCR é candidato.
_BINARY_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp"}


def assess_extraction_quality(text: str, original_path: Path) -> dict[str, Any]:
    """Avalia objetivamente se a extração textual foi suficiente.

    Sinais (sem número mágico único): quantidade de caracteres extraídos, tamanho
    do arquivo original e densidade texto/tamanho. Para documentos binários
    (PDF/imagem), pouca densidade indica PDF escaneado sem camada textual.
    Retorna metadados que são gravados no extraction_metadata (JSON) — sem coluna nova.
    """
    char_count = len((text or "").strip())
    try:
        original_bytes = original_path.stat().st_size
    except OSError:
        original_bytes = 0
    suffix = original_path.suffix.lower()
    is_binary = suffix in _BINARY_SUFFIXES

    # Densidade: caracteres por KB do arquivo original. PDF escaneado tende a ser
    # grande em bytes e produzir pouquíssimo texto.
    kb = max(original_bytes / 1024.0, 0.001)
    chars_per_kb = char_count / kb

    sufficient = True
    reason: str | None = None
    if is_binary:
        if char_count < settings.extraction_min_chars:
            sufficient = False
            reason = f"texto extraído insuficiente ({char_count} caracteres)"
        elif original_bytes > 0 and chars_per_kb < settings.extraction_min_chars_per_kb:
            sufficient = False
            reason = f"baixa densidade de texto ({chars_per_kb:.2f} chars/KB) para arquivo de {original_bytes} bytes"

    return {
        "char_count": char_count,
        "original_bytes": original_bytes,
        "chars_per_kb": round(chars_per_kb, 2),
        "is_binary": is_binary,
        "extraction_quality": "SUFICIENTE" if sufficient else "INSUFICIENTE",
        "extraction_insufficient_reason": reason,
    }


class DocumentNormalizer:
    """Normaliza formatos suportados sem substituir o original armazenado.

    Detecta extração textual insuficiente (ex.: matrícula escaneada) e, quando
    OCR local estiver habilitado e disponível, extrai o texto por página via OCR.
    Nunca substitui o documento original; o resultado do OCR é apenas a camada
    textual normalizada, com rastreabilidade preservada no metadata.
    """

    def normalize(self, original_path: Path, document_type: str) -> tuple[str, dict[str, Any]]:
        metadata: dict[str, Any] = {"engine": "MarkItDown", "document_type": document_type, "ocr": False, "ocr_available": ocr_available()}
        text = ""
        try:
            from markitdown import MarkItDown
            result = MarkItDown().convert(str(original_path))
            text = result.text_content or ""
            metadata.update({"title": getattr(result, "title", None)})
        except Exception as exc:
            if original_path.suffix.lower() in {".txt", ".md", ".csv"}:
                metadata.update({"engine": "texto-direto", "fallback_reason": str(exc)})
                text = original_path.read_text(encoding="utf-8", errors="replace")
            else:
                # Documento binário que o MarkItDown não converteu: candidato a OCR.
                metadata.update({"engine": "falha-markitdown", "fallback_reason": str(exc)})
                text = ""

        quality = assess_extraction_quality(text, original_path)
        metadata.update(quality)

        if quality["extraction_quality"] == "INSUFICIENTE":
            log.info("extracao insuficiente detectada: arquivo=%s motivo=%s ocr_habilitado=%s ocr_disponivel=%s",
                     original_path.name, quality.get("extraction_insufficient_reason"), settings.ocr_enabled, metadata["ocr_available"])
            if settings.ocr_enabled and metadata["ocr_available"]:
                try:
                    ocr_text, ocr_meta = run_ocr(original_path, settings.ocr_language)
                    if len((ocr_text or "").strip()) > quality["char_count"]:
                        metadata.update(ocr_meta)
                        metadata["engine"] = "OCR"
                        metadata["extraction_quality"] = "OCR"
                        metadata["char_count"] = len(ocr_text.strip())
                        return ocr_text, metadata
                    metadata["ocr_note"] = "OCR executado, mas não melhorou a extração"
                except Exception as exc:  # OCR falhou: registra e segue sem quebrar
                    metadata["ocr_error"] = str(exc)[:500]
                    log.warning("ocr falhou: arquivo=%s erro=%s", original_path.name, str(exc)[:200])
            else:
                # Limitação registrada: OCR não habilitado/indisponível neste ambiente.
                metadata["ocr_pending"] = True

        # Se nem MarkItDown nem OCR produziram texto e o arquivo não é texto simples,
        # ainda assim não quebra: devolve o que houver (pode ser vazio) com metadata
        # indicando extração insuficiente, permitindo tratamento a jusante.
        if not text and metadata.get("engine") == "falha-markitdown":
            raise RuntimeError(f"Não foi possível normalizar o documento e OCR indisponível: {metadata.get('fallback_reason')}")
        return text, metadata

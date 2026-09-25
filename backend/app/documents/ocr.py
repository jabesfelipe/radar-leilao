"""OCR local-first opcional para documentos com extração textual insuficiente.

Local-first: não usa serviço cloud nem API externa. Tenta usar um motor de OCR
disponível localmente (Tesseract via pytesseract + pdf2image para PDFs). Se as
dependências não estiverem instaladas no ambiente, o OCR fica indisponível e o
pipeline apenas registra a limitação — nunca quebra e nunca substitui o original.

Para habilitar OCR no ambiente Docker, é necessário instalar as dependências de
sistema (tesseract-ocr, tesseract-ocr-por, poppler-utils) e Python
(pytesseract, pdf2image, pillow), além de LLM_/OCR flag OCR_ENABLED=true.
Enquanto isso não estiver provisionado, esta função retorna disponível=False.
"""
from __future__ import annotations

from pathlib import Path

from ..logging_config import get_logger

log = get_logger("ocr")

_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tiff", ".bmp"}


def ocr_available() -> bool:
    """Indica se um motor de OCR local está disponível neste ambiente."""
    try:
        import pytesseract  # noqa: F401
        return True
    except Exception:
        return False


def run_ocr(original_path: Path, language: str = "por") -> tuple[str, dict[str, object]]:
    """Extrai texto por página via OCR local. Retorna (texto, metadata).

    metadata inclui: ocr=True, ocr_engine, ocr_language, ocr_pages, ocr_available.
    Levanta RuntimeError se o motor não estiver disponível — o chamador deve
    tratar essa condição como limitação e seguir sem OCR.
    """
    if not ocr_available():
        raise RuntimeError("Motor de OCR local (pytesseract) indisponível no ambiente")

    import pytesseract
    from PIL import Image

    suffix = original_path.suffix.lower()
    pages_text: list[str] = []

    if suffix == ".pdf":
        try:
            from pdf2image import convert_from_path
        except Exception as exc:  # pdf2image/poppler ausentes
            raise RuntimeError(f"OCR de PDF indisponível (pdf2image/poppler): {exc}") from exc
        images = convert_from_path(str(original_path))
        for page_number, image in enumerate(images, start=1):
            text = pytesseract.image_to_string(image, lang=language) or ""
            # Marca a página para preservar rastreabilidade (page) no chunking.
            pages_text.append(f"## Página {page_number}\n\n{text.strip()}")
    elif suffix in _IMAGE_SUFFIXES:
        text = pytesseract.image_to_string(Image.open(original_path), lang=language) or ""
        pages_text.append(f"## Página 1\n\n{text.strip()}")
    else:
        raise RuntimeError(f"OCR não suportado para a extensão {suffix}")

    full_text = "\n\n".join(part for part in pages_text if part.strip())
    metadata = {
        "ocr": True,
        "ocr_engine": "tesseract",
        "ocr_language": language,
        "ocr_pages": len(pages_text),
        "ocr_available": True,
    }
    log.info("ocr concluido: arquivo=%s paginas=%d chars=%d", original_path.name, len(pages_text), len(full_text))
    return full_text, metadata

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

from ..config import settings
from ..logging_config import get_logger

log = get_logger("ocr")

_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tiff", ".bmp"}


def ocr_available() -> bool:
    """Indica se um motor de OCR local está disponível neste ambiente.

    Exige o pacote Python (``pytesseract``) E o binário do Tesseract no PATH. Antes bastava
    importar o pacote: sem o binário, ``ocr_available`` dizia True e o OCR falhava só na
    hora de rodar, escondendo a limitação.
    """
    try:
        import pytesseract
    except Exception:
        return False
    import shutil
    return shutil.which(getattr(pytesseract.pytesseract, "tesseract_cmd", "tesseract") or "tesseract") is not None


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
        try:
            from pdf2image import pdfinfo_from_path
            total_pages = int(pdfinfo_from_path(str(original_path)).get("Pages") or 0)
        except Exception:
            total_pages = 0
        # Limite de páginas: protege memória/CPU da VPS e o tempo da requisição de upload.
        max_pages = max(1, int(settings.ocr_max_pages))
        if total_pages > 0:
            # Uma página por vez: converter o PDF inteiro para imagens ocuparia dezenas de MB por página
            # ao mesmo tempo (60 páginas estourariam o limite de memória do contêiner).
            images_iter = (convert_from_path(str(original_path), first_page=n, last_page=n)[0] for n in range(1, min(total_pages, max_pages) + 1))
        else:
            images_iter = iter(convert_from_path(str(original_path), first_page=1, last_page=max_pages))
        for page_number, image in enumerate(images_iter, start=1):
            text = pytesseract.image_to_string(image, lang=language, timeout=int(settings.ocr_page_timeout_seconds)) or ""
            # Marca a página para preservar rastreabilidade (page) no chunking.
            pages_text.append(f"## Página {page_number}\n\n{text.strip()}")
    elif suffix in _IMAGE_SUFFIXES:
        text = pytesseract.image_to_string(Image.open(original_path), lang=language, timeout=int(settings.ocr_page_timeout_seconds)) or ""
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
    if suffix == ".pdf" and total_pages and total_pages > len(pages_text):
        # Páginas além do limite NÃO foram lidas: registra para a UI/auditoria não fingir leitura completa.
        metadata["ocr_pages_total"] = total_pages
        metadata["ocr_truncated"] = True
    log.info("ocr concluido: arquivo=%s paginas=%d chars=%d", original_path.name, len(pages_text), len(full_text))
    return full_text, metadata

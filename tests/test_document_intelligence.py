"""Testes de Document Intelligence (TASK 65).

Cobrem a detecção objetiva de extração insuficiente e o gancho de OCR opcional.
Não exigem banco: exercitam assess_extraction_quality e DocumentNormalizer com
arquivos temporários, além do import-guard de OCR.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from backend.app.documents.normalizer import DocumentNormalizer, assess_extraction_quality
from backend.app.documents import ocr as ocr_module


def test_texto_suficiente_nao_marca_insuficiente(tmp_path: Path):
    arquivo = tmp_path / "edital.txt"
    conteudo = "Edital de leilão. " * 200  # texto abundante
    arquivo.write_text(conteudo, encoding="utf-8")
    quality = assess_extraction_quality(conteudo, arquivo)
    assert quality["extraction_quality"] == "SUFICIENTE"
    assert quality["char_count"] > 0
    assert quality["is_binary"] is False


def test_pdf_com_pouco_texto_e_detectado_insuficiente(tmp_path: Path):
    # Simula uma matrícula escaneada: arquivo .pdf "grande" mas com texto mínimo.
    arquivo = tmp_path / "matricula.pdf"
    arquivo.write_bytes(b"%PDF-1.4\n" + b"0" * 50_000)  # ~50 KB de bytes binários
    texto_extraido = "autenticidade CNS codigo de verificacao"  # < extraction_min_chars
    quality = assess_extraction_quality(texto_extraido, arquivo)
    assert quality["is_binary"] is True
    assert quality["extraction_quality"] == "INSUFICIENTE"
    assert quality["extraction_insufficient_reason"]


def test_pdf_com_texto_denso_e_suficiente(tmp_path: Path):
    arquivo = tmp_path / "edital.pdf"
    conteudo = "Cláusula de responsabilidade e comissão do leiloeiro. " * 200
    arquivo.write_bytes(conteudo.encode("utf-8"))
    quality = assess_extraction_quality(conteudo, arquivo)
    assert quality["is_binary"] is True
    assert quality["extraction_quality"] == "SUFICIENTE"


def test_normalizer_txt_gera_quality_suficiente(tmp_path: Path):
    arquivo = tmp_path / "doc.txt"
    arquivo.write_text("Conteúdo textual real do documento. " * 50, encoding="utf-8")
    texto, metadata = DocumentNormalizer().normalize(arquivo, "Outro")
    assert "documento" in texto.lower()
    assert metadata["extraction_quality"] == "SUFICIENTE"
    assert metadata["ocr"] is False
    assert "char_count" in metadata and "original_bytes" in metadata


def test_normalizer_registra_ocr_pending_quando_indisponivel(tmp_path: Path, monkeypatch):
    # Força extração insuficiente e OCR habilitado, mas motor indisponível:
    # o pipeline registra a limitação (ocr_pending) e NÃO quebra.
    monkeypatch.setattr("backend.app.documents.normalizer.settings.ocr_enabled", True, raising=False)
    monkeypatch.setattr("backend.app.documents.normalizer.ocr_available", lambda: False)

    arquivo = tmp_path / "matricula.pdf"
    arquivo.write_bytes(b"%PDF-1.4\n" + b"0" * 40_000)

    # MarkItDown retorna texto mínimo (simula PDF escaneado sem camada textual).
    class _FakeResult:
        text_content = "autenticidade CNS"
        title = None

    class _FakeMarkItDown:
        def convert(self, _path):
            return _FakeResult()

    import backend.app.documents.normalizer as norm
    monkeypatch.setattr("markitdown.MarkItDown", _FakeMarkItDown, raising=False)

    texto, metadata = DocumentNormalizer().normalize(arquivo, "Matrícula")
    assert metadata["extraction_quality"] == "INSUFICIENTE"
    assert metadata.get("ocr_pending") is True
    assert metadata["ocr"] is False  # OCR não aplicado


def test_normalizer_aplica_ocr_quando_disponivel(tmp_path: Path, monkeypatch):
    # Extração insuficiente + OCR habilitado e disponível: usa o texto do OCR,
    # marca ocr=True e preserva a rastreabilidade (metadata).
    monkeypatch.setattr("backend.app.documents.normalizer.settings.ocr_enabled", True, raising=False)
    monkeypatch.setattr("backend.app.documents.normalizer.ocr_available", lambda: True)

    ocr_text = "## Página 1\n\n" + ("Registro de imóveis matrícula 25278 consolidação. " * 20)

    def _fake_run_ocr(path, language="por"):
        return ocr_text, {"ocr": True, "ocr_engine": "tesseract", "ocr_language": language, "ocr_pages": 1, "ocr_available": True}

    monkeypatch.setattr("backend.app.documents.normalizer.run_ocr", _fake_run_ocr)

    arquivo = tmp_path / "matricula.pdf"
    arquivo.write_bytes(b"%PDF-1.4\n" + b"0" * 40_000)

    class _FakeResult:
        text_content = "autenticidade CNS"
        title = None

    class _FakeMarkItDown:
        def convert(self, _path):
            return _FakeResult()

    monkeypatch.setattr("markitdown.MarkItDown", _FakeMarkItDown, raising=False)

    texto, metadata = DocumentNormalizer().normalize(arquivo, "Matrícula")
    assert "matrícula 25278" in texto.lower()
    assert metadata["ocr"] is True
    assert metadata["extraction_quality"] == "OCR"
    assert metadata["ocr_engine"] == "tesseract"
    assert metadata["ocr_pages"] == 1


def test_ocr_run_indisponivel_levanta_runtimeerror(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(ocr_module, "ocr_available", lambda: False)
    with pytest.raises(RuntimeError):
        ocr_module.run_ocr(tmp_path / "x.pdf")

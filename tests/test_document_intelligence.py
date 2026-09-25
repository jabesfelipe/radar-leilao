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


def test_ocr_desabilitado_mantem_comportamento_sem_ocr(tmp_path: Path, monkeypatch):
    # Extração insuficiente + OCR DESABILITADO (default do projeto): o pipeline
    # NÃO aplica OCR e registra a limitação (ocr_pending), sem quebrar.
    monkeypatch.setattr("backend.app.documents.normalizer.settings.ocr_enabled", False, raising=False)
    # Mesmo que o motor esteja disponível, a flag desabilitada tem precedência.
    monkeypatch.setattr("backend.app.documents.normalizer.ocr_available", lambda: True)

    def _run_ocr_nao_deve_ser_chamado(path, language="por"):
        raise AssertionError("run_ocr não deveria ser chamado com OCR desabilitado")

    monkeypatch.setattr("backend.app.documents.normalizer.run_ocr", _run_ocr_nao_deve_ser_chamado)

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
    assert metadata["ocr"] is False
    assert metadata["extraction_quality"] == "INSUFICIENTE"
    assert metadata.get("ocr_pending") is True
    assert texto == "autenticidade CNS"


def test_ocr_preserva_marcadores_de_pagina_multipagina(tmp_path: Path, monkeypatch):
    # OCR de PDF de múltiplas páginas: os marcadores "## Página N" precisam ser
    # preservados no texto normalizado para manter rastreabilidade no chunking.
    monkeypatch.setattr("backend.app.documents.normalizer.settings.ocr_enabled", True, raising=False)
    monkeypatch.setattr("backend.app.documents.normalizer.settings.ocr_language", "por", raising=False)
    monkeypatch.setattr("backend.app.documents.normalizer.ocr_available", lambda: True)

    ocr_text = (
        "## Página 1\n\n" + ("Matrícula 25278 registro de imóveis Curitiba. " * 12)
        + "\n\n## Página 2\n\n" + ("Averbações e consolidação de propriedade. " * 12)
    )
    idioma_recebido: dict[str, str] = {}

    def _fake_run_ocr(path, language="por"):
        idioma_recebido["lang"] = language
        return ocr_text, {"ocr": True, "ocr_engine": "tesseract", "ocr_language": language, "ocr_pages": 2, "ocr_available": True}

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
    assert "## Página 1" in texto and "## Página 2" in texto
    assert metadata["ocr"] is True
    assert metadata["ocr_pages"] == 2
    # O idioma configurado (por) é repassado ao motor de OCR.
    assert idioma_recebido["lang"] == "por"


def test_run_ocr_usa_portugues_por_padrao(monkeypatch, tmp_path: Path):
    # run_ocr deve usar o idioma "por" por padrão e repassá-lo ao tesseract.
    monkeypatch.setattr(ocr_module, "ocr_available", lambda: True)

    capturado: dict[str, str] = {}

    class _FakePyTesseract:
        @staticmethod
        def image_to_string(_image, lang="eng"):
            capturado["lang"] = lang
            return "texto ocr da pagina"

    class _FakeImage:
        @staticmethod
        def open(_path):
            return object()

    def _fake_convert_from_path(_path):
        return [object()]

    monkeypatch.setitem(__import__("sys").modules, "pytesseract", _FakePyTesseract)
    monkeypatch.setitem(__import__("sys").modules, "PIL", type("PIL", (), {"Image": _FakeImage}))
    import types as _types
    _pdf2image = _types.ModuleType("pdf2image")
    _pdf2image.convert_from_path = _fake_convert_from_path
    monkeypatch.setitem(__import__("sys").modules, "pdf2image", _pdf2image)

    arquivo = tmp_path / "matricula.pdf"
    arquivo.write_bytes(b"%PDF-1.4\n0000")

    texto, metadata = ocr_module.run_ocr(arquivo)
    assert capturado["lang"] == "por"
    assert metadata["ocr_language"] == "por"
    assert metadata["ocr_pages"] == 1
    assert "## Página 1" in texto


def test_normalizer_nao_substitui_arquivo_original(tmp_path: Path, monkeypatch):
    # O OCR gera apenas a camada textual normalizada; o arquivo original em disco
    # NÃO pode ser modificado nem substituído pelo pipeline.
    monkeypatch.setattr("backend.app.documents.normalizer.settings.ocr_enabled", True, raising=False)
    monkeypatch.setattr("backend.app.documents.normalizer.ocr_available", lambda: True)

    ocr_text = "## Página 1\n\n" + ("Registro de imóveis matrícula 25278. " * 20)

    def _fake_run_ocr(path, language="por"):
        return ocr_text, {"ocr": True, "ocr_engine": "tesseract", "ocr_language": language, "ocr_pages": 1, "ocr_available": True}

    monkeypatch.setattr("backend.app.documents.normalizer.run_ocr", _fake_run_ocr)

    arquivo = tmp_path / "matricula.pdf"
    conteudo_original = b"%PDF-1.4\n" + b"0" * 40_000
    arquivo.write_bytes(conteudo_original)
    bytes_antes = arquivo.stat().st_size

    class _FakeResult:
        text_content = "autenticidade CNS"
        title = None

    class _FakeMarkItDown:
        def convert(self, _path):
            return _FakeResult()

    monkeypatch.setattr("markitdown.MarkItDown", _FakeMarkItDown, raising=False)

    texto, metadata = DocumentNormalizer().normalize(arquivo, "Matrícula")
    # Original intacto: mesmo tamanho e mesmos bytes.
    assert arquivo.exists()
    assert arquivo.stat().st_size == bytes_antes
    assert arquivo.read_bytes() == conteudo_original
    # Texto normalizado veio do OCR (não é o arquivo original).
    assert metadata["ocr"] is True
    assert "matrícula 25278" in texto.lower()

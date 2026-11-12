"""Validação de uploads (upload_security): nome seguro, tamanho, vazio, MIME e assinatura."""
from __future__ import annotations

import asyncio
import io
import zipfile
from io import BytesIO

import pytest
from fastapi import HTTPException, UploadFile

from backend.app import upload_security as us

PDF = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n%%EOF\n"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 16
OLE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 32


def _ooxml(prefix: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")
        zf.writestr(f"{prefix}document.xml", "<doc/>")
    return buf.getvalue()


# ---------------------------------------------------------------- nome de arquivo

@pytest.mark.parametrize("raw,esperado", [
    ("matricula.pdf", "matricula.pdf"),
    ("Edital 2026 (1).PDF", "Edital 2026 (1).PDF"),
    ("../../etc/passwd.txt", "passwd.txt"),
    ("..\\..\\windows\\sistema.txt", "sistema.txt"),
    ("C:\\Users\\x\\matrícula final.pdf", "matrícula final.pdf"),
    ("nome\twith\x07control.txt", "nomewithcontrol.txt"),
    ("a;b&c|d.txt", "a_b_c_d.txt"),
    (".oculto.txt", "oculto.txt"),
])
def test_sanitize_filename_remove_caminho_e_caracteres_perigosos(raw, esperado):
    assert us.sanitize_filename(raw) == esperado


@pytest.mark.parametrize("raw", ["", "..", ".", "arquivo.exe", "script.pdf.exe", "sem_extensao", "nulo\x00.pdf", "...", "x.PHP"])
def test_sanitize_filename_rejeita_invalidos(raw):
    # "" cai no nome padrão "documento" (sem extensão permitida) => rejeitado
    with pytest.raises(ValueError):
        us.sanitize_filename(raw)


def test_sanitize_filename_limita_comprimento_preservando_extensao():
    nome = us.sanitize_filename("a" * 400 + ".pdf")
    assert len(nome) <= 150 and nome.endswith(".pdf")


# ---------------------------------------------------------------- conteúdo

def test_arquivo_valido_de_cada_tipo():
    assert us.validate_upload("a.pdf", "application/pdf", PDF) == "a.pdf"
    assert us.validate_upload("a.png", "image/png", PNG) == "a.png"
    assert us.validate_upload("a.jpg", "image/jpeg", JPG) == "a.jpg"
    assert us.validate_upload("a.jpeg", None, JPG) == "a.jpeg"
    assert us.validate_upload("a.doc", "application/msword", OLE) == "a.doc"
    assert us.validate_upload("a.xls", "application/vnd.ms-excel", OLE) == "a.xls"
    assert us.validate_upload("a.docx", "application/octet-stream", _ooxml("word/")) == "a.docx"
    assert us.validate_upload("a.xlsx", "", _ooxml("xl/")) == "a.xlsx"
    assert us.validate_upload("a.txt", "text/plain; charset=utf-8", "olá mundo".encode()) == "a.txt"
    assert us.validate_upload("a.csv", "application/vnd.ms-excel", b"a;b\n1;2\n") == "a.csv"
    assert us.validate_upload("a.md", "text/markdown", b"# titulo") == "a.md"


def test_extensao_falsa_conteudo_nao_corresponde():
    with pytest.raises(HTTPException) as exc:
        us.validate_upload("matricula.pdf", "application/pdf", b"MZ\x90\x00 executavel disfarcado")
    assert exc.value.status_code == 400
    for nome, conteudo in [("a.png", PDF), ("a.jpg", PNG), ("a.doc", PDF), ("a.pdf", PNG)]:
        with pytest.raises(HTTPException) as exc:
            us.validate_upload(nome, None, conteudo)
        assert exc.value.status_code == 400


def test_arquivo_vazio_recusado():
    with pytest.raises(HTTPException) as exc:
        us.validate_upload("a.pdf", "application/pdf", b"")
    assert exc.value.status_code == 400 and "vazio" in exc.value.detail


def test_acima_do_limite_413():
    with pytest.raises(HTTPException) as exc:
        us.validate_upload("a.txt", "text/plain", b"x" * 2048, max_bytes=1024)
    assert exc.value.status_code == 413


def test_mime_incompativel_415_e_generico_aceito():
    with pytest.raises(HTTPException) as exc:
        us.validate_upload("a.pdf", "text/html", PDF)
    assert exc.value.status_code == 415
    assert us.validate_upload("a.pdf", "application/octet-stream", PDF) == "a.pdf"


def test_ooxml_corrompido_ou_sem_estrutura():
    with pytest.raises(HTTPException) as exc:
        us.validate_upload("a.docx", None, b"PK\x03\x04 lixo que nao e zip")
    assert exc.value.status_code == 400
    with pytest.raises(HTTPException) as exc:
        us.validate_upload("a.docx", None, _ooxml("xl/"))  # zip válido, mas é uma planilha
    assert exc.value.status_code == 400


def test_zip_bomb_recusado(monkeypatch):
    monkeypatch.setattr(us, "_MAX_UNCOMPRESSED", 10)
    with pytest.raises(HTTPException) as exc:
        us.validate_upload("a.docx", None, _ooxml("word/"))
    assert exc.value.status_code == 400 and "limite" in exc.value.detail


def test_texto_com_byte_nulo_recusado():
    with pytest.raises(HTTPException) as exc:
        us.validate_upload("a.txt", "text/plain", b"abc\x00def")
    assert exc.value.status_code == 400


def test_mensagens_nao_ecoam_conteudo():
    segredo = b"SEGREDO-NO-ARQUIVO-123"
    with pytest.raises(HTTPException) as exc:
        us.validate_upload("a.pdf", None, segredo)
    assert "SEGREDO" not in exc.value.detail


# ---------------------------------------------------------------- leitura limitada

def test_read_limited_interrompe_ao_ultrapassar_o_limite():
    file = UploadFile(filename="a.txt", file=BytesIO(b"x" * (3 * 1024 * 1024)))
    with pytest.raises(HTTPException) as exc:
        asyncio.run(us.read_limited(file, max_bytes=1024 * 1024))
    assert exc.value.status_code == 413
    # leu no máximo o limite + uma parte (não o arquivo inteiro de 3 MB)
    assert file.file.tell() <= 2 * 1024 * 1024


def test_read_limited_le_arquivo_pequeno_inteiro():
    file = UploadFile(filename="a.txt", file=BytesIO(b"conteudo"))
    assert asyncio.run(us.read_limited(file, max_bytes=1024)) == b"conteudo"

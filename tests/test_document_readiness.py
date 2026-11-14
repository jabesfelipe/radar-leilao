"""Estados de processamento de documentos e prontidão para análise (P0 — homologação v1.0.2).

Usa o pipeline REAL (MarkItDown + chunking + PostgreSQL). Simulações só onde a fronteira externa
é inevitável: o motor de OCR (Tesseract não existe no ambiente de CI) e o provider de embeddings
(sem chave). Nada aqui chama a OpenAI.
"""
from __future__ import annotations

import pytest

from backend.app import models
from backend.app.config import settings
from backend.app.documents import dedup, states, worker
from backend.app.documents.pipeline import DocumentPipeline
from backend.app.documents.readiness import property_documents_summary, version_processing
from backend.app.rag.retriever import HybridRetriever

# PDF de uma página SEM camada de texto (equivalente a um documento escaneado).
PDF_SEM_TEXTO = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]>>endobj\ntrailer<</Root 1 0 R/Size 4>>\n%%EOF\n"
)
TEXTO = ("Matrícula consolidada em nome do credor fiduciário. Imóvel livre de ônus conhecidos. " * 40).encode()


@pytest.fixture(autouse=True)
def _sem_chave_e_storage(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    monkeypatch.setattr(settings, "openai_api_key", None)
    monkeypatch.setattr(settings, "llm_api_key", None)
    monkeypatch.setattr(settings, "ocr_enabled", False)


def _doc(db, tipo="MATRICULA", nome="doc.txt"):
    prop = models.Property(title="Imóvel Doc", address="Rua X", city="São Paulo", state="SP", area_m2=60, bedrooms=2)
    db.add(prop); db.flush()
    doc = models.Document(property_id=prop.id, name=nome, document_type=tipo, source="teste")
    db.add(doc); db.flush()
    return prop, doc


def _etapa(info, nome):
    return next(e for e in info["etapas"] if e["etapa"] == nome)


def test_texto_digital_sem_chave_fica_pronto_por_texto_e_nao_indexado(db):
    _, doc = _doc(db)
    v = DocumentPipeline(db).ingest(doc, TEXTO, "matricula.txt")
    info = version_processing(db, v)
    assert v.status == states.CONCLUIDO            # nunca INDEXADO sem embedding
    assert info["estado"] == "PRONTO_SEM_EMBEDDING" and info["pronto_para_analise"] is True
    assert info["nivel_indexacao"] == "texto" and info["chunks"] > 0 and info["chunks_com_embedding"] == 0
    assert [e["etapa"] for e in info["etapas"]] == ["upload", "ocr", "extracao", "chunking", "embedding", "indexacao"]
    assert _etapa(info, "ocr")["estado"] == "nao_aplicavel"
    assert _etapa(info, "extracao")["estado"] == "concluida" and _etapa(info, "chunking")["estado"] == "concluida"
    assert _etapa(info, "embedding")["estado"] == "indisponivel"   # sem chave
    assert _etapa(info, "indexacao")["estado"] == "parcial"        # só texto


def test_arquivo_sem_texto_nao_e_apresentado_como_processado(db):
    _, doc = _doc(db, nome="vazio.txt")
    v = DocumentPipeline(db).ingest(doc, b"   \n  ", "vazio.txt")
    info = version_processing(db, v)
    assert v.status == states.SEM_TEXTO and doc.status == states.SEM_TEXTO
    assert info["estado"] == "SEM_TEXTO" and info["pronto_para_analise"] is False and info["chunks"] == 0
    assert _etapa(info, "extracao")["estado"] == "falhou"
    assert _etapa(info, "indexacao")["estado"] == "falhou"
    assert "Não está pronto" in info["mensagem"]


def test_pdf_digitalizado_com_ocr_desligado_vira_ocr_necessario(db):
    _, doc = _doc(db, nome="escaneado.pdf")
    v = DocumentPipeline(db).ingest(doc, PDF_SEM_TEXTO, "escaneado.pdf")
    info = version_processing(db, v)
    assert v.status == states.OCR_NECESSARIO and doc.status == states.OCR_NECESSARIO
    assert info["estado"] == "OCR_NECESSARIO" and info["pronto_para_analise"] is False
    ocr = _etapa(info, "ocr")
    assert ocr["estado"] == "indisponivel" and "desligado" in ocr["detalhe"]
    assert v.extraction_metadata.get("ocr_pending") is True


def test_pdf_digitalizado_com_ocr_ligado_mas_motor_ausente_informa_indisponibilidade(db, monkeypatch):
    monkeypatch.setattr(settings, "ocr_enabled", True)
    monkeypatch.setattr("backend.app.documents.normalizer.ocr_available", lambda: False)
    _, doc = _doc(db, nome="escaneado.pdf")
    v = DocumentPipeline(db).ingest(doc, PDF_SEM_TEXTO, "escaneado.pdf")
    info = version_processing(db, v)
    assert v.status == states.OCR_NECESSARIO
    assert "motor de OCR não está disponível" in _etapa(info, "ocr")["detalhe"]


def test_ocr_bem_sucedido_torna_o_documento_pronto(db, monkeypatch):
    monkeypatch.setattr(settings, "ocr_enabled", True)
    monkeypatch.setattr("backend.app.documents.normalizer.ocr_available", lambda: True)
    texto_ocr = "## Página 1\n\n" + ("Matrícula 12345 averbação de consolidação da propriedade fiduciária. " * 8)
    monkeypatch.setattr("backend.app.documents.normalizer.run_ocr", lambda path, lang: (texto_ocr, {"ocr": True, "ocr_engine": "tesseract", "ocr_language": lang, "ocr_pages": 1, "ocr_available": True}))
    _, doc = _doc(db, nome="escaneado.pdf")
    v = DocumentPipeline(db).ingest(doc, PDF_SEM_TEXTO, "escaneado.pdf")
    info = version_processing(db, v)
    assert v.status == states.CONCLUIDO and info["pronto_para_analise"] is True
    assert _etapa(info, "ocr")["estado"] == "concluida"
    assert v.extraction_metadata["engine"] == "OCR"


def test_ocr_que_falha_gera_ocr_falhou_sem_quebrar_o_upload(db, monkeypatch):
    monkeypatch.setattr(settings, "ocr_enabled", True)
    monkeypatch.setattr("backend.app.documents.normalizer.ocr_available", lambda: True)

    def _explode(path, lang):
        raise RuntimeError("tesseract caiu: /tmp/segredo.pdf")

    monkeypatch.setattr("backend.app.documents.normalizer.run_ocr", _explode)
    _, doc = _doc(db, nome="escaneado.pdf")
    v = DocumentPipeline(db).ingest(doc, PDF_SEM_TEXTO, "escaneado.pdf")
    info = version_processing(db, v)
    assert v.status == states.OCR_FALHOU and info["pronto_para_analise"] is False
    assert _etapa(info, "ocr")["estado"] == "falhou"
    # a mensagem bruta do erro (com caminho) não vai para a etapa exibida ao usuário
    assert "segredo.pdf" not in str(info)


def test_ocr_que_nao_melhora_a_extracao_tambem_e_falha_explicita(db, monkeypatch):
    monkeypatch.setattr(settings, "ocr_enabled", True)
    monkeypatch.setattr("backend.app.documents.normalizer.ocr_available", lambda: True)
    monkeypatch.setattr("backend.app.documents.normalizer.run_ocr", lambda path, lang: ("", {"ocr": True, "ocr_available": True}))
    _, doc = _doc(db, nome="escaneado.pdf")
    v = DocumentPipeline(db).ingest(doc, PDF_SEM_TEXTO, "escaneado.pdf")
    assert v.status == states.OCR_FALHOU


class _EmbedFake:
    def __init__(self, nulos=()):
        self.nulos = set(nulos)

    def embed(self, texts):
        return [None if i in self.nulos else [0.1] * settings.embedding_dimensions for i, _ in enumerate(texts)]


def _com_chave(monkeypatch, gateway):
    monkeypatch.setattr(settings, "openai_api_key", "sk-teste-nao-e-real")
    monkeypatch.setattr("backend.app.documents.embedding.build_gateway", lambda: gateway)


TEXTO_LONGO = (("Cláusula sobre ocupação e débitos condominiais do imóvel objeto do leilão. " * 20) + "\n\n") * 6


def test_embeddings_completos_marcam_indexado_e_vetorial(db, monkeypatch):
    _com_chave(monkeypatch, _EmbedFake())
    _, doc = _doc(db)
    v = DocumentPipeline(db).ingest(doc, TEXTO_LONGO.encode(), "longo.txt")
    info = version_processing(db, v)
    assert info["chunks"] > 1
    assert v.status == states.INDEXADO and info["estado"] == "INDEXADO" and info["nivel_indexacao"] == "vetorial"
    assert _etapa(info, "embedding")["estado"] == "concluida" and _etapa(info, "indexacao")["estado"] == "concluida"


def test_embeddings_parciais_NAO_marcam_indexado(db, monkeypatch):
    _com_chave(monkeypatch, _EmbedFake(nulos={1}))
    _, doc = _doc(db)
    v = DocumentPipeline(db).ingest(doc, TEXTO_LONGO.encode(), "longo.txt")
    info = version_processing(db, v)
    assert info["chunks"] > 1 and 0 < info["chunks_com_embedding"] < info["chunks"]
    assert v.status == states.CONCLUIDO            # antes: INDEXADO com um único vetor
    assert info["estado"] == "INDEXADO_PARCIAL" and info["nivel_indexacao"] == "parcial"
    assert _etapa(info, "embedding")["estado"] == "parcial"


def test_falha_do_provider_de_embedding_nao_derruba_o_upload_e_fica_pendente(db, monkeypatch):
    class Quebrado:
        def embed(self, texts):
            raise ConnectionError("rede fora")

    _com_chave(monkeypatch, Quebrado())
    _, doc = _doc(db)
    v = DocumentPipeline(db).ingest(doc, TEXTO, "m.txt")
    info = version_processing(db, v)
    assert v.status == states.CONCLUIDO and info["pronto_para_analise"] is True
    assert info["nivel_indexacao"] == "texto" and _etapa(info, "embedding")["estado"] in {"pendente", "falhou"}


def _versao_nao_pronta(db, monkeypatch):
    """Versão COM chunks mas sem texto utilizável (extração insuficiente, OCR indisponível)."""
    def _normalize(self, path, document_type):
        return "texto curto", {"engine": "MarkItDown", "document_type": document_type, "ocr": False, "ocr_available": False, "char_count": 11, "extraction_quality": "INSUFICIENTE", "ocr_pending": True}

    monkeypatch.setattr("backend.app.documents.pipeline.DocumentNormalizer.normalize", _normalize)
    prop, doc = _doc(db, nome="escaneado.pdf")
    v = DocumentPipeline(db).ingest(doc, PDF_SEM_TEXTO, "escaneado.pdf")
    assert v.status == states.OCR_NECESSARIO
    return prop, doc, v


def test_versao_nao_pronta_fica_fora_do_rag_e_da_fila_de_embeddings(db, monkeypatch):
    prop, _, v = _versao_nao_pronta(db, monkeypatch)
    chunks = db.query(models.DocumentChunk).filter(models.DocumentChunk.document_version_id == v.id).count()
    assert chunks > 0
    assert HybridRetriever(db).search("texto curto", property_id=prop.id) == []
    assert v.id not in worker.pending_versions(db)


def test_resumo_do_imovel_conta_documentos_prontos_e_nao_prontos(db, monkeypatch):
    prop, _, _ = _versao_nao_pronta(db, monkeypatch)
    monkeypatch.undo()
    monkeypatch.setattr(settings, "storage_dir", settings.storage_dir)
    ok = models.Document(property_id=prop.id, name="ok.txt", document_type="EDITAL", source="t")
    db.add(ok); db.flush()
    monkeypatch.setattr(settings, "openai_api_key", None)
    DocumentPipeline(db).ingest(ok, TEXTO, "ok.txt")
    resumo = property_documents_summary(db, prop.id)
    assert resumo["total"] == 2 and resumo["prontos"] == 1
    assert [i["estado"] for i in resumo["nao_prontos"]] == ["OCR_NECESSARIO"]


def test_reenvio_do_mesmo_arquivo_apos_ocr_ligado_reprocessa_em_vez_de_reaproveitar(db, monkeypatch):
    _, doc = _doc(db, nome="escaneado.pdf")
    v1 = DocumentPipeline(db).ingest(doc, PDF_SEM_TEXTO, "escaneado.pdf")
    assert v1.status == states.OCR_NECESSARIO
    assert dedup.find_reusable_version(doc, dedup.content_digest(PDF_SEM_TEXTO)) is None
    db.refresh(doc)
    v2 = DocumentPipeline(db).ingest(doc, PDF_SEM_TEXTO, "escaneado.pdf")
    assert v2.id != v1.id and v2.version == v1.version + 1

"""GET /api/imoveis/{id}: o campo "imovel" traz só as colunas do imóvel (v1.0.4).

Regressão da 1ª execução real com OpenAI no caso-01: o endpoint devolvia o objeto ORM e o jsonable_encoder
serializava todo relacionamento já carregado (documentos, chunks com texto bruto e embedding, caminho do
arquivo, evidências sem máscara). Com embeddings (numpy) a resposta virava HTTP 500; sem eles, o texto bruto
do documento, com dados pessoais, ia para o navegador.
"""
from __future__ import annotations

import json

import pytest
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from backend.app import models
from backend.app.config import settings
from backend.app.database import get_db
from backend.app.main import app

try:
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover
    TestClient = None

CPF = "123.456.789-09"
TEXTO_MATRICULA = f"MATRÍCULA nº 12.345. Área privativa de 62,00 m². Proprietário FULANO FICTÍCIO, CPF {CPF}."
TEXTO_EDITAL = "EDITAL. Imóvel objeto da matrícula nº 12.345, área privativa de 62,00 m²."


@pytest.fixture
def ambiente(postgres_engine):
    if TestClient is None:
        pytest.skip("fastapi.testclient (httpx) indisponível")
    if "properties" not in set(inspect(postgres_engine).get_table_names()):
        pytest.skip("Migrations do Radar ainda não aplicadas no banco de testes")
    connection = postgres_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, autoflush=False, join_transaction_mode="create_savepoint")
    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app), session
    finally:
        app.dependency_overrides.pop(get_db, None)
        session.close()
        transaction.rollback()
        connection.close()


def _imovel_com_matricula_e_edital(session: Session) -> int:
    vetor = [0.1] * settings.embedding_dimensions  # chunks com embedding, como após a indexação com IA
    prop = models.Property(title="Imóvel payload", address="Rua Fictícia 1", city="São Paulo", state="SP", area_m2=62, bedrooms=2)
    session.add(prop)
    session.flush()
    for i, (tipo, texto) in enumerate((("MATRICULA", TEXTO_MATRICULA), ("EDITAL", TEXTO_EDITAL))):
        doc = models.Document(property_id=prop.id, name=f"{tipo.lower()}.txt", document_type=tipo)
        session.add(doc)
        session.flush()
        versao = models.DocumentVersion(document_id=doc.id, version=1, content_hash=str(i) * 64,
                                        original_path=f"/srv/storage/segredo/{tipo.lower()}.txt", normalized_markdown=texto)
        session.add(versao)
        session.flush()
        session.add(models.DocumentChunk(document_version_id=versao.id, chunk_index=0, content=texto, page=1,
                                         section="1", metadata_json={}, embedding=vetor))
    session.flush()
    return prop.id


def test_detalhe_com_chunks_indexados_responde_200_sem_vazar_relacionamentos(ambiente):
    client, session = ambiente
    pid = _imovel_com_matricula_e_edital(session)

    resposta = client.get(f"/api/imoveis/{pid}")

    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    colunas = {attr.key for attr in inspect(models.Property).column_attrs}
    assert set(corpo["imovel"]) <= colunas
    assert corpo["imovel"]["id"] == pid and corpo["imovel"]["title"] == "Imóvel payload"
    for relacao in ("documents", "evidences", "analyses", "auctions", "costs", "debts"):
        assert relacao not in corpo["imovel"]
    bruto = json.dumps(corpo, ensure_ascii=False)
    assert CPF not in bruto  # o confronto documental mostra o trecho, mas mascarado
    assert "/srv/storage/segredo" not in bruto
    assert "embedding" not in bruto
    # O confronto documental continua funcionando com os chunks carregados.
    assert {linha["resultado"] for linha in corpo["confronto_documental"]} == {"CONFERE"}

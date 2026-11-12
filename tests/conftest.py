import os

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

from backend.app import models
from backend.app.config import settings


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "security_gate: executa o teste COM o portão de segurança global ativo (sem o bypass padrão da suíte)",
    )


@pytest.fixture(autouse=True)
def _security_gate_bypass(request):
    """Os testes de domínio (financeiro, checklist, RAG...) exercitam regras de negócio via
    TestClient sem se autenticar. Para não duplicar o login em centenas de testes, o portão
    global de segurança (``security_gate``) é substituído por um no-op — o mesmo mecanismo
    de ``dependency_overrides`` já usado para ``get_db``. Os testes de segurança usam o
    marcador ``@pytest.mark.security_gate`` e rodam com o portão REAL. As dependências por
    rota (RBAC de admin, usuários, oportunidades) permanecem ativas em todos os testes.
    """
    from backend.app.main import app
    from backend.app.security import reset_limits, security_gate

    reset_limits()
    if request.node.get_closest_marker("security_gate"):
        yield
        reset_limits()
        return
    app.dependency_overrides[security_gate] = lambda: None
    try:
        yield
    finally:
        app.dependency_overrides.pop(security_gate, None)


@pytest.fixture(scope="session")
def postgres_engine():
    database_url = os.getenv("RAG_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("RAG_TEST_DATABASE_URL não configurada; testes de integração exigem PostgreSQL explícito")
    engine = create_engine(database_url, pool_pre_ping=True, connect_args={"connect_timeout": 3})
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            connection.execute(text("SELECT '[1,0]'::vector"))
            required = {"properties", "documents", "document_versions", "document_chunks"}
            if not required.issubset(set(inspect(connection).get_table_names())):
                pytest.skip("PostgreSQL disponível, mas migrations do Radar ainda não foram aplicadas")
    except Exception as exc:
        pytest.skip(f"PostgreSQL/pgvector indisponível: {exc}")
    return engine


@pytest.fixture
def db(postgres_engine):
    session = Session(postgres_engine)
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def documents(db):
    vector_a = [1.0] + [0.0] * (settings.embedding_dimensions - 1)
    vector_b = [0.0, 1.0] + [0.0] * (settings.embedding_dimensions - 2)
    property_a = models.Property(title="Imóvel A", address="Rua A", city="São Paulo", state="SP", area_m2=70, bedrooms=2)
    property_b = models.Property(title="Imóvel B", address="Rua B", city="São Paulo", state="SP", area_m2=80, bedrooms=3)
    db.add_all([property_a, property_b])
    db.flush()
    document_a = models.Document(property_id=property_a.id, name="matricula-a.pdf", document_type="Matrícula")
    document_b = models.Document(property_id=property_b.id, name="edital-b.pdf", document_type="Edital")
    db.add_all([document_a, document_b])
    db.flush()
    version_a = models.DocumentVersion(document_id=document_a.id, version=1, content_hash="a" * 64, original_path="a.pdf", normalized_markdown="# A")
    version_b = models.DocumentVersion(document_id=document_b.id, version=1, content_hash="b" * 64, original_path="b.pdf", normalized_markdown="# B")
    db.add_all([version_a, version_b])
    db.flush()
    db.add_all([
        models.DocumentChunk(document_version_id=version_a.id, chunk_index=0, content="matrícula consolidada propriedade imóvel alfa", page=2, section="AV-1", metadata_json={"category": "juridico"}, embedding=vector_a),
        models.DocumentChunk(document_version_id=version_a.id, chunk_index=1, content="condomínio e matrícula do imóvel alfa", page=3, section="Débitos", metadata_json={"category": "financeiro"}, embedding=None),
        models.DocumentChunk(document_version_id=version_b.id, chunk_index=0, content="matrícula consolidada propriedade imóvel beta", page=4, section="AV-2", metadata_json={"category": "juridico"}, embedding=vector_b),
    ])
    db.flush()
    return {"property_a": property_a.id, "property_b": property_b.id, "document_a": document_a.id, "version_a": version_a.id}

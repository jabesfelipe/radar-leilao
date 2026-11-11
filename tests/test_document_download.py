"""Download autenticado de documentos (hospedagem): 401 sem token, 200 com token,
404 para caminho fora da raiz do storage. Dados sintéticos (nunca o imóvel 633)."""
from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from backend.app import models, auth
from backend.app.config import settings
from backend.app.database import get_db
from backend.app.main import app

try:
    from fastapi.testclient import TestClient
except Exception:  # pragma: no cover
    TestClient = None


@pytest.fixture
def client(postgres_engine, monkeypatch, tmp_path):
    if TestClient is None:
        pytest.skip("TestClient indisponível")
    monkeypatch.setattr(settings, "jwt_secret_key", "segredo-dl-teste", raising=False)
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path / "documents"))
    monkeypatch.setattr(settings, "storage_backend", "local", raising=False)
    connection = postgres_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, autoflush=False, join_transaction_mode="create_savepoint")

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)
        session.close(); transaction.rollback(); connection.close()


def _session():
    return next(app.dependency_overrides[get_db]())


def _seed(tmp_path, original_path_override=None):
    s = _session()
    s.add(models.User(email="dl@t.com", name="DL", password_hash=auth.hash_password("senha-forte-123"), role="CONSULTA", active=True))
    prop = models.Property(title="Imovel DL", address="Rua DL", city="Curitiba", state="PR", area_m2=50, bedrooms=1)
    s.add(prop); s.flush()
    doc = models.Document(property_id=prop.id, name="a.txt", document_type="Outro", source="Manual")
    s.add(doc); s.flush()
    f = tmp_path / "documents" / f"property-{prop.id}" / "original" / "v1-a.txt"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_bytes(b"conteudo sintetico")
    ver = models.DocumentVersion(document_id=doc.id, version=1, content_hash="e" * 64,
                                 original_path=original_path_override or str(f), status="CONCLUIDO")
    s.add(ver); s.flush()
    return ver.id


def _token(client):
    return client.post("/api/auth/login", json={"email": "dl@t.com", "password": "senha-forte-123"}).json()["access_token"]


def test_download_exige_autenticacao(client, tmp_path):
    vid = _seed(tmp_path)
    assert client.get(f"/api/documentos/versoes/{vid}/arquivo").status_code == 401


def test_download_autenticado_retorna_conteudo(client, tmp_path):
    vid = _seed(tmp_path)
    r = client.get(f"/api/documentos/versoes/{vid}/arquivo", headers={"Authorization": f"Bearer {_token(client)}"})
    assert r.status_code == 200 and r.content == b"conteudo sintetico"
    assert "attachment" in r.headers["content-disposition"]


def test_download_recusa_caminho_fora_da_raiz(client, tmp_path):
    outside = tmp_path / "fora.txt"; outside.write_bytes(b"segredo")
    vid = _seed(tmp_path, original_path_override=str(outside))
    r = client.get(f"/api/documentos/versoes/{vid}/arquivo", headers={"Authorization": f"Bearer {_token(client)}"})
    assert r.status_code == 404

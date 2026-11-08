"""Fase 4: abstração de storage (local) + governança de arquivos (dry-run).

Nunca exclui nada por padrão; nunca toca o imóvel 633. Dados sintéticos.
"""
from __future__ import annotations

from pathlib import Path

from backend.app import models
from backend.app.storage.local import LocalStorage
from backend.app.storage import build_storage
from backend.app.documents import storage_governance as gov


# --------------------------------------------------------------------------
# Abstração de storage (LocalStorage) — puro filesystem
# --------------------------------------------------------------------------

def test_local_storage_round_trip(tmp_path):
    st = LocalStorage(tmp_path)
    obj = st.write_bytes("property-1/original/v1-x.pdf", b"conteudo")
    assert obj.key == "property-1/original/v1-x.pdf"
    assert st.exists("property-1/original/v1-x.pdf")
    assert st.read_bytes("property-1/original/v1-x.pdf") == b"conteudo"
    assert st.backend_name() == "local"


def test_local_storage_impede_path_traversal(tmp_path):
    st = LocalStorage(tmp_path)
    import pytest
    with pytest.raises(ValueError):
        st.write_bytes("../fora.txt", b"x")


def test_build_storage_default_local(monkeypatch):
    from backend.app.config import settings
    monkeypatch.setattr(settings, "storage_backend", "local", raising=False)
    st = build_storage(settings)
    assert st.backend_name() == "local"


# --------------------------------------------------------------------------
# Governança: diagnóstico dry-run (usa DB real p/ checar properties)
# --------------------------------------------------------------------------

def _make_storage_tree(tmp_path: Path, ids_dir: list[str]):
    base = tmp_path / "documents"
    for name in ids_dir:
        d = base / name / "original"
        d.mkdir(parents=True, exist_ok=True)
        (d / "v1-x.pdf").write_bytes(b"x" * 100)
    return tmp_path


def test_diagnose_classifica_orfao_referenciado_e_protegido(db, tmp_path):
    # Cria um imóvel real para referenciar um dos diretórios.
    prop = models.Property(title="Imovel GOV", address="Rua GOV", city="Curitiba", state="PR", area_m2=70, bedrooms=2)
    db.add(prop); db.flush()

    _make_storage_tree(tmp_path, [f"property-{prop.id}", "property-999999", "property-633", "lixo-fora-do-padrao"])
    rep = gov.diagnose(db, tmp_path)

    by_name = {d["name"]: d for d in rep["diretorios"]}
    assert by_name[f"property-{prop.id}"]["classification"] == gov.REFERENCED
    assert by_name["property-999999"]["classification"] == gov.NOT_REFERENCED
    assert by_name["property-633"]["classification"] == gov.UNCERTAIN  # protegido
    assert by_name["property-633"]["protected"] is True
    assert by_name["lixo-fora-do-padrao"]["classification"] == gov.UNCERTAIN
    assert "property-999999" in rep["candidatos_limpeza"]
    assert "property-633" not in rep["candidatos_limpeza"]
    assert rep["espaco_recuperavel_bytes"] >= 100


def test_cleanup_dry_run_nao_remove_nada(db, tmp_path):
    _make_storage_tree(tmp_path, ["property-888888"])
    plano = gov.cleanup(db, tmp_path)  # defaults: dry_run=True
    assert plano["dry_run"] is True
    assert plano["removidos"] == []
    assert "dry-run" in plano["motivo"]
    # Diretório continua existindo (nada removido).
    assert (tmp_path / "documents" / "property-888888").exists()


def test_cleanup_protege_633_mesmo_se_confirmado(db, tmp_path):
    _make_storage_tree(tmp_path, ["property-633"])
    plano = gov.cleanup(db, tmp_path, dry_run=False, allow_delete=True, confirm_names=["property-633"])
    assert plano["removidos"] == []  # 633 nunca é removido
    assert (tmp_path / "documents" / "property-633").exists()

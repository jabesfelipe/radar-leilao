"""Serviço de cobertura municipal por tipo de débito (Etapa B).

Determinístico, sem LLM e SEM consulta externa. Esta etapa apenas CADASTRA e
consulta a MATRIZ de cobertura (município × tipo de débito) — nenhuma consulta de
débito real é executada; coletores/adaptadores são etapas futuras (ver a
especificação de adaptadores). A cobertura vive como DADO administrável, nunca em
condicionais fixas no backend; o seed abaixo é a cobertura INICIAL honesta, derivada
do levantamento de existência de portais públicos (sem confirmar débitos).

Regras honestas (ausência de investigação ≠ ausência de débito):
  - Só o IPTU dos 4 municípios tem portal público de consulta identificado → nível
    ``AUTOMATIZAVEL`` (potencialmente automatizável; NÃO automatizado nesta etapa).
  - Dívida ativa, taxas, certidões e demais tipos permanecem ``NAO_INVESTIGADA`` /
    método ``MANUAL`` até análise dedicada de viabilidade e termos de uso.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models


class CoverageError(ValueError):
    """Erro de validação de cobertura (tipo/município inexistente, vocabulário inválido)."""


# Cobertura inicial como DADO. Chave: (name, state) do município → lista de entradas.
# Cada entrada descreve um tipo de débito e o estado honesto da cobertura.
# IDENTIFICADOR exigido reflete o levantamento (ex.: Curitiba usa Inscrição Imobiliária
# ou Indicação Fiscal). NENHUMA consulta real foi feita.
_IPTU_AUTOMATIZAVEL = {
    "debt_type_code": "IPTU",
    "level": "AUTOMATIZAVEL",
    "situation": "DISPONIVEL",
    "method": "PORTAL_PUBLICO",
}
_MANUAL_NAO_INVESTIGADA = {
    "level": "NAO_INVESTIGADA",
    "situation": "NAO_INVESTIGADA",
    "method": "MANUAL",
}

COVERAGE_SEED: dict[tuple[str, str], list[dict[str, Any]]] = {
    ("Curitiba", "PR"): [
        {**_IPTU_AUTOMATIZAVEL, "identifier_required": "Inscrição Imobiliária + Sublote ou Indicação Fiscal",
         "observations": "Portal IPTU-DAM (iptu-dam.curitiba.pr.gov.br). Viabilidade de automação depende de termos de uso."},
        {"debt_type_code": "DIVIDA_ATIVA_MUNICIPAL", **_MANUAL_NAO_INVESTIGADA},
        {"debt_type_code": "TAXA_MUNICIPAL", **_MANUAL_NAO_INVESTIGADA},
    ],
    ("São José dos Pinhais", "PR"): [
        {**_IPTU_AUTOMATIZAVEL, "identifier_required": "Inscrição/cadastro imobiliário (a confirmar)",
         "observations": "Portal de Finanças (financas.sjp.pr.gov.br / Semfi). Viabilidade de automação não confirmada."},
        {"debt_type_code": "DIVIDA_ATIVA_MUNICIPAL", **_MANUAL_NAO_INVESTIGADA},
        {"debt_type_code": "TAXA_MUNICIPAL", **_MANUAL_NAO_INVESTIGADA},
    ],
    ("Fazenda Rio Grande", "PR"): [
        {**_IPTU_AUTOMATIZAVEL, "identifier_required": "A investigar",
         "observations": "Divisão de Arrecadação (fazendariogrande.pr.gov.br). Possível plataforma atende.net; não confirmado."},
        {"debt_type_code": "DIVIDA_ATIVA_MUNICIPAL", **_MANUAL_NAO_INVESTIGADA},
        {"debt_type_code": "TAXA_MUNICIPAL", **_MANUAL_NAO_INVESTIGADA},
    ],
    ("Assis", "SP"): [
        {**_IPTU_AUTOMATIZAVEL, "identifier_required": "Cadastro do imóvel (a confirmar)",
         "observations": "Sistema de Arrecadação (tributacao.assis.sp.gov.br). NÃO confundir com a capital de SP."},
        {"debt_type_code": "DIVIDA_ATIVA_MUNICIPAL", **_MANUAL_NAO_INVESTIGADA},
        {"debt_type_code": "TAXA_MUNICIPAL", **_MANUAL_NAO_INVESTIGADA},
    ],
}


def _validate_vocab(level: str, situation: str, method: str) -> None:
    if level not in models.COVERAGE_LEVELS:
        raise CoverageError(f"Nível de cobertura inválido: {level}")
    if situation not in models.DEBT_SOURCE_SITUATIONS:
        raise CoverageError(f"Situação inválida: {situation}")
    if method not in models.DEBT_CONSULTATION_METHODS:
        raise CoverageError(f"Método de consulta inválido: {method}")


def _require_debt_type(db: Session, code: str) -> models.DebtType:
    dt = db.scalar(select(models.DebtType).where(models.DebtType.code == code))
    if dt is None:
        raise CoverageError(f"Tipo de débito desconhecido: {code!r}. Cadastre em debt_types.")
    return dt


def seed_coverage(db: Session) -> int:
    """Materializa a cobertura inicial como DADO (idempotente por município × tipo).

    Depende dos municípios e tipos já semeados (Etapa A). Retorna nº de linhas criadas.
    Não sobrescreve cobertura existente (edições do operador são preservadas)."""
    created = 0
    for (name, state), entries in COVERAGE_SEED.items():
        muni = db.scalar(
            select(models.Municipality).where(
                models.Municipality.name == name, models.Municipality.state == state
            )
        )
        if muni is None:
            continue  # município ainda não semeado; seed de municípios roda antes
        for entry in entries:
            code = entry["debt_type_code"]
            # Só semeia tipos existentes no catálogo (evita cobertura órfã).
            if db.scalar(select(models.DebtType).where(models.DebtType.code == code)) is None:
                continue
            exists = db.scalar(
                select(models.MunicipalityCoverage).where(
                    models.MunicipalityCoverage.municipality_id == muni.id,
                    models.MunicipalityCoverage.debt_type_code == code,
                )
            )
            if exists is not None:
                continue
            db.add(models.MunicipalityCoverage(
                municipality_id=muni.id,
                debt_type_code=code,
                level=entry.get("level", "NAO_INVESTIGADA"),
                situation=entry.get("situation", "NAO_INVESTIGADA"),
                method=entry.get("method", "INDEFINIDO"),
                identifier_required=entry.get("identifier_required"),
                observations=entry.get("observations"),
            ))
            created += 1
    db.flush()
    return created


def create_coverage(db: Session, data: dict[str, Any]) -> models.MunicipalityCoverage:
    """Cria uma linha de cobertura município × tipo. Valida referências e vocabulário;
    recusa duplicidade (unicidade município × tipo)."""
    municipality_id = data["municipality_id"]
    code = data["debt_type_code"]
    if db.get(models.Municipality, municipality_id) is None:
        raise CoverageError("municipality_id inexistente")
    _require_debt_type(db, code)
    level = (data.get("level") or "NAO_INVESTIGADA").upper()
    situation = (data.get("situation") or "NAO_INVESTIGADA").upper()
    method = (data.get("method") or "INDEFINIDO").upper()
    _validate_vocab(level, situation, method)
    source_id = data.get("source_id")
    if source_id is not None:
        src = db.get(models.DebtSource, source_id)
        if src is None or src.municipality_id != municipality_id:
            raise CoverageError("source_id inexistente ou de outro município")
    exists = db.scalar(
        select(models.MunicipalityCoverage).where(
            models.MunicipalityCoverage.municipality_id == municipality_id,
            models.MunicipalityCoverage.debt_type_code == code,
        )
    )
    if exists is not None:
        raise CoverageError("Cobertura já existe para este município × tipo (use edição)")
    item = models.MunicipalityCoverage(
        municipality_id=municipality_id,
        debt_type_code=code,
        level=level,
        situation=situation,
        method=method,
        active=data.get("active", True),
        source_id=source_id,
        identifier_required=data.get("identifier_required"),
        limitations=data.get("limitations"),
        observations=data.get("observations"),
    )
    db.add(item)
    db.flush()
    return item


def update_coverage(db: Session, item: models.MunicipalityCoverage, changes: dict[str, Any]) -> models.MunicipalityCoverage:
    """Edita cobertura existente. Revalida vocabulário quando alterado; valida a fonte.
    Marca ``last_validated_at`` quando o operador registra validação da cobertura."""
    merged_level = (changes.get("level") or item.level).upper()
    merged_situation = (changes.get("situation") or item.situation).upper()
    merged_method = (changes.get("method") or item.method).upper()
    _validate_vocab(merged_level, merged_situation, merged_method)
    if "source_id" in changes and changes["source_id"] is not None:
        src = db.get(models.DebtSource, changes["source_id"])
        if src is None or src.municipality_id != item.municipality_id:
            raise CoverageError("source_id inexistente ou de outro município")
    for field in ("level", "situation", "method"):
        if field in changes and changes[field] is not None:
            changes[field] = changes[field].upper()
    # Validação registrada pelo operador atualiza o carimbo de última validação.
    if changes.pop("mark_validated", False):
        item.last_validated_at = datetime.utcnow()
    for k, v in changes.items():
        setattr(item, k, v)
    db.flush()
    return item


def coverage_matrix(db: Session, municipality_id: int | None = None) -> dict[str, Any]:
    """Matriz de cobertura (leitura pura). Opcionalmente filtra por município.

    Lista cada combinação município × tipo com nível/situação/método/ativo e os tipos
    de débito ATIVOS que ainda NÃO têm cobertura registrada (cobertura não investigada),
    para que a ausência fique visível (ausência de dado ≠ ausência de débito)."""
    stmt = select(models.MunicipalityCoverage)
    if municipality_id is not None:
        stmt = stmt.where(models.MunicipalityCoverage.municipality_id == municipality_id)
    rows = db.scalars(stmt.order_by(
        models.MunicipalityCoverage.municipality_id, models.MunicipalityCoverage.debt_type_code
    )).all()

    munis = db.scalars(select(models.Municipality).order_by(models.Municipality.name)).all()
    if municipality_id is not None:
        munis = [m for m in munis if m.id == municipality_id]
    active_types = db.scalars(select(models.DebtType).where(models.DebtType.active.is_(True))).all()
    type_codes = {t.code for t in active_types}

    by_muni: dict[int, set[str]] = {}
    itens: list[dict[str, Any]] = []
    for r in rows:
        by_muni.setdefault(r.municipality_id, set()).add(r.debt_type_code)
        itens.append({
            "id": r.id, "municipality_id": r.municipality_id, "debt_type_code": r.debt_type_code,
            "level": r.level, "situation": r.situation, "method": r.method, "active": r.active,
            "source_id": r.source_id, "identifier_required": r.identifier_required,
            "limitations": r.limitations, "observations": r.observations,
            "last_validated_at": r.last_validated_at,
        })

    nao_investigados: list[dict[str, Any]] = []
    for m in munis:
        cobertos = by_muni.get(m.id, set())
        for code in sorted(type_codes - cobertos):
            nao_investigados.append({"municipality_id": m.id, "debt_type_code": code, "level": "NAO_INVESTIGADA"})

    return {
        "total": len(itens),
        "itens": itens,
        "nao_investigados": nao_investigados,
        "ressalva": "Cobertura não investigada não implica ausência de débito; é um estado a ser apurado.",
    }

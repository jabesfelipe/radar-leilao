"""Orquestração de consulta de débito (Etapa E): seleção de provider, execução com
retry controlado, persistência da execução (``DebtQuery``) e do resultado normalizado
(``PropertyDebt`` reusado), histórico e rastreabilidade.

Camadas separadas (SPEC-ADAPTADORES): o provider faz a CONSULTA; este serviço cuida da
NORMALIZAÇÃO (via ``debts_service.normalize_debt_payload``), PERSISTÊNCIA e EVENTO. A
CONSOLIDAÇÃO fica em ``debts_service.consolidate`` (leitura).

Determinístico; nenhuma chamada externa real. O provider manual/assistido é o fallback
sempre válido. ``timeout_s``/``max_attempts`` são parametrizáveis pelo chamador (retry
controlado apenas para status transitório ``INDISPONIVEL``/``ERRO``).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from . import models, debts_service, debt_providers
from .services import record_event, record_history

_TRANSIENT = {"INDISPONIVEL", "ERRO"}


def run_query(
    db: Session,
    prop: "models.Property",
    *,
    debt_type_code: str,
    municipality_id: int | None = None,
    source_id: int | None = None,
    identifier: str | None = None,
    payload: dict[str, Any] | None = None,
    max_attempts: int = 1,
) -> dict[str, Any]:
    """Executa UMA consulta via provider selecionado por (município × tipo), persiste
    a execução e, quando houver resultado, cria o(s) ``PropertyDebt`` normalizado(s).

    Retorna um dicionário com a execução, os débitos criados e a consolidação atual."""
    # Valida o tipo no catálogo (mesma regra do registro manual).
    if db.scalar(debts_service.select(models.DebtType).where(models.DebtType.code == debt_type_code)) is None:
        raise ValueError(f"Tipo de débito desconhecido: {debt_type_code!r}. Cadastre em debt_types.")

    provider = debt_providers.select_provider(db, municipality_id=municipality_id, debt_type_code=debt_type_code)
    ctx = debt_providers.DebtQueryContext(
        property_id=prop.id, debt_type_code=debt_type_code, municipality_id=municipality_id,
        source_id=source_id, identifier=identifier, payload=payload or {},
    )

    attempts = 0
    result: debt_providers.DebtQueryResult | None = None
    max_attempts = max(1, min(int(max_attempts), 5))  # retry controlado e limitado
    while attempts < max_attempts:
        attempts += 1
        result = provider.consultar(db, ctx)
        if result.status not in _TRANSIENT:
            break  # só re-tenta falhas transitórias

    assert result is not None
    query = models.DebtQuery(
        property_id=prop.id, opportunity_id=None, municipality_id=municipality_id,
        debt_type_code=debt_type_code, provider=result.provider, provider_version=result.provider_version,
        mode=result.mode, status=result.status, source_id=source_id, identifier=identifier,
        requested_at=datetime.utcnow(), completed_at=datetime.utcnow(),
        duration_ms=result.duration_ms, attempts=attempts, message=result.message,
    )
    db.add(query); db.flush()

    created: list[models.PropertyDebt] = []
    for raw in result.items:
        try:
            normalized = debts_service.normalize_debt_payload(db, raw)
        except ValueError:
            continue  # item inválido não derruba a consulta inteira
        debt = models.PropertyDebt(
            property_id=prop.id,
            municipality_id=municipality_id,
            source_id=source_id,
            acquisition_method=f"{result.provider}:{result.mode}",
            queried_at=query.completed_at,
            **{k: v for k, v in normalized.items() if k not in {"municipality_id"}},
        )
        db.add(debt); db.flush()
        created.append(debt)
        if query.debt_id is None:
            query.debt_id = debt.id

    event = record_event(db, prop, "CONSULTA_DEBITO_EXECUTADA", "DebtQuery", query.id,
                         {"provider": result.provider, "status": result.status, "debt_type_code": debt_type_code,
                          "debitos_criados": len(created)}, ["financeiro", "checklist"])
    record_history(db, prop, "DebtQuery", query.id, "CREATE", None,
                   {"status": result.status, "provider": result.provider}, event.id)

    from .services import serialize
    return {
        "consulta": {
            "id": query.id, "status": query.status, "provider": query.provider, "mode": query.mode,
            "attempts": query.attempts, "duration_ms": query.duration_ms, "message": query.message,
            "debt_type_code": query.debt_type_code, "municipality_id": query.municipality_id,
            "debt_id": query.debt_id,
        },
        "debitos_criados": [d.id for d in created],
        "consolidacao": serialize(debts_service.consolidate(db, prop.id)),
        "evento_id": event.id,
    }


def list_queries(db: Session, property_id: int) -> list[dict[str, Any]]:
    """Histórico de consultas do imóvel (leitura pura)."""
    rows = db.scalars(
        debts_service.select(models.DebtQuery).where(models.DebtQuery.property_id == property_id).order_by(models.DebtQuery.id.desc())
    ).all()
    return [
        {
            "id": q.id, "debt_type_code": q.debt_type_code, "municipality_id": q.municipality_id,
            "provider": q.provider, "mode": q.mode, "status": q.status, "attempts": q.attempts,
            "duration_ms": q.duration_ms, "message": q.message, "debt_id": q.debt_id,
            "requested_at": q.requested_at, "completed_at": q.completed_at,
        }
        for q in rows
    ]

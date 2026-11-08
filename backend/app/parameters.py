"""Catálogo CENTRAL de parâmetros administráveis + serviço de resolução (Etapa A).

Fundação TRANSVERSAL (não específica de débitos): qualquer módulo (financeiro,
risco, mercado, checklist, débitos, …) resolve parâmetros por aqui, com precedência
e versionamento. Determinístico, sem LLM. Segredos NUNCA entram neste catálogo.

Precedência de resolução (do mais específico ao mais geral) para uma ``key`` e um
contexto ``(municipality_id, debt_category)``:
  1. MUNICIPIO_CATEGORIA  (município + categoria exatos)
  2. MUNICIPIO            (município exato)
  3. CATEGORIA            (categoria exata)
  4. GLOBAL
  5. ``default_value`` do registro encontrado (ou o ``default`` explícito do chamador)

Só parâmetros ``status=ATIVO`` e dentro da vigência (``valid_from``/``valid_until``)
são considerados na resolução. O histórico é imutável (append-only).
"""
from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models


class ParameterError(ValueError):
    """Erro de validação/definição de parâmetro (entrada inválida do administrador)."""


# ---------------------------------------------------------------------------
# Conversão de valor serializado <-> tipado (determinística, validada)
# ---------------------------------------------------------------------------

def coerce_value(raw: str | None, data_type: str) -> Any:
    """Converte o valor serializado (texto) para o tipo declarado. ``None`` permanece
    ``None``. Levanta ``ParameterError`` quando o texto não casa com o tipo."""
    if raw is None:
        return None
    dt = (data_type or "STRING").upper()
    try:
        if dt == "STRING":
            return str(raw)
        if dt == "INTEGER":
            return int(str(raw).strip())
        if dt == "DECIMAL":
            return Decimal(str(raw).strip())
        if dt == "BOOLEAN":
            return str(raw).strip().lower() in {"1", "true", "t", "sim", "yes", "y"}
        if dt == "JSON":
            parsed = json.loads(raw)
            return parsed
        raise ParameterError(f"Tipo de dado não suportado: {data_type}")
    except (ValueError, InvalidOperation, json.JSONDecodeError) as exc:
        raise ParameterError(f"Valor '{raw}' inválido para o tipo {dt}: {exc}") from exc


def serialize_value(value: Any, data_type: str) -> str | None:
    """Serializa um valor tipado para texto de persistência (inverso de coerce_value)."""
    if value is None:
        return None
    dt = (data_type or "STRING").upper()
    if dt == "JSON":
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if dt == "BOOLEAN":
        return "true" if bool(value) else "false"
    return str(value)


def _validate_definition(
    *, data_type: str, scope: str, value: str | None, allowed_values: list | None,
    min_value: Decimal | None, max_value: Decimal | None,
) -> None:
    if data_type.upper() not in models.PARAMETER_DATA_TYPES:
        raise ParameterError(f"data_type inválido: {data_type}")
    if scope.upper() not in models.PARAMETER_SCOPES:
        raise ParameterError(f"scope inválido: {scope}")
    # Valida que o valor casa com o tipo (coerce levanta se inválido).
    typed = coerce_value(value, data_type)
    if typed is None:
        return
    if allowed_values:
        # Comparação por valor serializado simples (string) para tipos escalares.
        if data_type.upper() != "JSON" and str(typed) not in {str(a) for a in allowed_values}:
            raise ParameterError(f"valor '{typed}' fora de allowed_values")
    if data_type.upper() in {"INTEGER", "DECIMAL"}:
        numeric = Decimal(str(typed))
        if min_value is not None and numeric < min_value:
            raise ParameterError(f"valor {numeric} abaixo do mínimo {min_value}")
        if max_value is not None and numeric > max_value:
            raise ParameterError(f"valor {numeric} acima do máximo {max_value}")


def _within_validity(param: models.Parameter, *, now: datetime | None = None) -> bool:
    now = now or datetime.utcnow()
    if param.valid_from is not None and now < param.valid_from:
        return False
    if param.valid_until is not None and now > param.valid_until:
        return False
    return True


# ---------------------------------------------------------------------------
# Escrita (com versionamento e histórico imutável)
# ---------------------------------------------------------------------------

def create_parameter(db: Session, data: dict[str, Any], *, actor: str = "sistema", justification: str | None = None) -> models.Parameter:
    scope = (data.get("scope") or "GLOBAL").upper()
    data_type = (data.get("data_type") or "STRING").upper()
    _validate_definition(
        data_type=data_type, scope=scope, value=data.get("value"),
        allowed_values=data.get("allowed_values"),
        min_value=data.get("min_value"), max_value=data.get("max_value"),
    )
    param = models.Parameter(
        key=data["key"], name=data.get("name") or data["key"], description=data.get("description"),
        category=data.get("category") or "geral", data_type=data_type, scope=scope,
        municipality_id=data.get("municipality_id"), debt_category=data.get("debt_category"),
        value=data.get("value"), default_value=data.get("default_value"), unit=data.get("unit"),
        allowed_values=data.get("allowed_values"), min_value=data.get("min_value"), max_value=data.get("max_value"),
        valid_from=data.get("valid_from"), valid_until=data.get("valid_until"),
        status=(data.get("status") or "ATIVO").upper(), version=1, updated_by=actor,
    )
    db.add(param)
    db.flush()
    db.add(models.ParameterHistory(
        parameter_id=param.id, key=param.key, version=1, previous_value=None,
        new_value=param.value, action="CREATE", actor=actor, justification=justification,
    ))
    db.flush()
    return param


def update_parameter(db: Session, param: models.Parameter, changes: dict[str, Any], *, actor: str = "sistema", justification: str | None = None) -> models.Parameter:
    """Aplica alteração gerando NOVA versão + registro de histórico (append-only).
    Nunca sobrescreve versões anteriores."""
    previous_value = param.value
    new_type = (changes.get("data_type") or param.data_type).upper()
    new_value = changes["value"] if "value" in changes else param.value
    _validate_definition(
        data_type=new_type, scope=(changes.get("scope") or param.scope).upper(), value=new_value,
        allowed_values=changes.get("allowed_values", param.allowed_values),
        min_value=changes.get("min_value", param.min_value), max_value=changes.get("max_value", param.max_value),
    )
    for field in ("name", "description", "category", "data_type", "unit", "allowed_values",
                  "min_value", "max_value", "valid_from", "valid_until", "value", "default_value"):
        if field in changes:
            setattr(param, field, changes[field])
    if "status" in changes:
        param.status = str(changes["status"]).upper()
    param.version += 1
    param.updated_by = actor
    db.flush()
    action = "UPDATE"
    if "status" in changes:
        action = "ACTIVATE" if param.status == "ATIVO" else "DEACTIVATE"
    db.add(models.ParameterHistory(
        parameter_id=param.id, key=param.key, version=param.version, previous_value=previous_value,
        new_value=param.value, action=action, actor=actor, justification=justification,
    ))
    db.flush()
    return param


# ---------------------------------------------------------------------------
# Resolução por precedência (serviço central — NUNCA reimplementar fora daqui)
# ---------------------------------------------------------------------------

def resolve(
    db: Session, key: str, *, municipality_id: int | None = None, debt_category: str | None = None,
    default: Any = None, now: datetime | None = None,
) -> Any:
    """Resolve o valor efetivo de ``key`` no contexto dado, tipado. Aplica a
    precedência (MUNICIPIO_CATEGORIA > MUNICIPIO > CATEGORIA > GLOBAL > default_value
    > default do chamador). Considera só ATIVO + dentro da vigência."""
    candidates = db.scalars(
        select(models.Parameter).where(models.Parameter.key == key, models.Parameter.status == "ATIVO")
    ).all()
    candidates = [p for p in candidates if _within_validity(p, now=now)]

    def _match(scope: str) -> models.Parameter | None:
        for p in candidates:
            if p.scope != scope:
                continue
            if scope == "MUNICIPIO_CATEGORIA" and p.municipality_id == municipality_id and p.debt_category == debt_category:
                return p
            if scope == "MUNICIPIO" and p.municipality_id == municipality_id:
                return p
            if scope == "CATEGORIA" and p.debt_category == debt_category:
                return p
            if scope == "GLOBAL":
                return p
        return None

    order = []
    if municipality_id is not None and debt_category is not None:
        order.append("MUNICIPIO_CATEGORIA")
    if municipality_id is not None:
        order.append("MUNICIPIO")
    if debt_category is not None:
        order.append("CATEGORIA")
    order.append("GLOBAL")

    for scope in order:
        param = _match(scope)
        if param is None:
            continue
        if param.value is not None:
            return coerce_value(param.value, param.data_type)
        if param.default_value is not None:
            return coerce_value(param.default_value, param.data_type)
    return default


def resolve_detail(
    db: Session, key: str, *, municipality_id: int | None = None, debt_category: str | None = None,
    default: Any = None, now: datetime | None = None,
) -> dict[str, Any]:
    """Como ``resolve``, mas retorna também a origem (parâmetro/escopo/versão) que
    determinou o valor — útil para snapshot de auditoria por execução."""
    value = resolve(db, key, municipality_id=municipality_id, debt_category=debt_category, default=default, now=now)
    # Reexecuta o matching só para reportar a origem (barato; mesma precedência).
    candidates = [
        p for p in db.scalars(select(models.Parameter).where(models.Parameter.key == key, models.Parameter.status == "ATIVO")).all()
        if _within_validity(p, now=now)
    ]
    origem = None
    order = (["MUNICIPIO_CATEGORIA"] if (municipality_id is not None and debt_category is not None) else []) \
        + (["MUNICIPIO"] if municipality_id is not None else []) \
        + (["CATEGORIA"] if debt_category is not None else []) + ["GLOBAL"]
    for scope in order:
        for p in candidates:
            if p.scope != scope:
                continue
            if scope == "MUNICIPIO_CATEGORIA" and (p.municipality_id, p.debt_category) == (municipality_id, debt_category):
                origem = p; break
            if scope == "MUNICIPIO" and p.municipality_id == municipality_id:
                origem = p; break
            if scope == "CATEGORIA" and p.debt_category == debt_category:
                origem = p; break
            if scope == "GLOBAL":
                origem = p; break
        if origem is not None:
            break
    return {
        "key": key, "value": value,
        "resolved_from": None if origem is None else {
            "parameter_id": origem.id, "scope": origem.scope, "version": origem.version,
            "municipality_id": origem.municipality_id, "debt_category": origem.debt_category,
        },
        "used_default": origem is None,
    }


# ---------------------------------------------------------------------------
# Snapshot de parâmetros por execução (imutabilidade de análises históricas)
# ---------------------------------------------------------------------------

# Chaves de parâmetros de negócio que influenciam a análise financeira/estimativas.
# Gravadas no snapshot de cada execução para que uma alteração administrativa futura
# NÃO altere retroativamente uma análise já realizada (invariante — preserva V1–V9).
FINANCE_PARAMETER_KEYS = (
    "mercado.amostra_minima",
    "mercado.cv_dispersao_alta",
    "condominio.periodo_presumido_meses",
    "condominio.margem_seguranca_pct",
    "condominio.fator_otimista",
    "checklist.idade_alerta_1_anos",
    "checklist.idade_alerta_2_anos",
)


def parameter_snapshot(db: Session, *, keys: tuple[str, ...] = FINANCE_PARAMETER_KEYS, now: datetime | None = None) -> list[dict[str, Any]]:
    """Resolve e retorna o snapshot (chave/valor/origem/versão) dos parâmetros de
    negócio no momento da execução. Determinístico; serializa valores como texto."""
    snapshot: list[dict[str, Any]] = []
    for key in keys:
        detail = resolve_detail(db, key, now=now)
        value = detail.get("value")
        detail["value"] = None if value is None else serialize_value(value, _data_type_for(db, key))
        snapshot.append(detail)
    return snapshot


def _data_type_for(db: Session, key: str) -> str:
    param = db.scalar(select(models.Parameter).where(models.Parameter.key == key))
    return param.data_type if param else "STRING"

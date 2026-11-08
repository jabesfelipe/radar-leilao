"""Seed idempotente dos parâmetros de negócio centralizados (Etapas C/D).

Retira valores de negócio hardcoded dos serviços e os disponibiliza no catálogo
central (``Parameter``), com chave semântica, categoria, unidade, tipo e valor
padrão. O consumo é feito via ``parameters.resolve`` (precedência + vigência) e o
snapshot por execução via ``parameters.resolve_detail``.

NUNCA inclui segredos, constantes técnicas de infraestrutura ou valores fiscais sem
fonte (ITBI/emolumentos ficam de fora: só entram com fonte oficial + vigência).
Determinístico e idempotente (não recria nem sobrescreve edições do operador).
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models

# Cada entrada define um parâmetro GLOBAL inicial. ``value`` é o valor serializado
# (texto). Chaves semânticas estáveis — os serviços resolvem por elas.
PARAMETER_SEED: tuple[dict[str, Any], ...] = (
    # --- Mercado (Etapa D: substitui market.MIN_SAMPLE / HIGH_DISPERSION_CV) ---
    {
        "key": "mercado.amostra_minima", "name": "Amostra mínima de comparáveis",
        "category": "mercado", "data_type": "INTEGER", "value": "7", "default_value": "7",
        "unit": "imóveis", "min_value": 1, "max_value": 100,
        "description": "Quantidade mínima de comparáveis para a estimativa de mercado ser considerada suficiente.",
    },
    {
        "key": "mercado.cv_dispersao_alta", "name": "CV de dispersão elevada",
        "category": "mercado", "data_type": "DECIMAL", "value": "0.30", "default_value": "0.30",
        "unit": "fração", "min_value": 0, "max_value": 5,
        "description": "Coeficiente de variação acima do qual a amostra é considerada dispersa/heterogênea.",
    },
    # --- Estimativa condominial (Etapa C) ---
    {
        "key": "condominio.periodo_presumido_meses", "name": "Período presumido de inadimplência",
        "category": "estimativa", "data_type": "INTEGER", "value": "12", "default_value": "12",
        "unit": "meses", "min_value": 0, "max_value": 120,
        "description": "Período PRESUMIDO de inadimplência condominial para a estimativa. NÃO é derivado da idade do imóvel/financiamento.",
    },
    {
        "key": "condominio.margem_seguranca_pct", "name": "Margem de segurança da estimativa condominial",
        "category": "estimativa", "data_type": "DECIMAL", "value": "0.10", "default_value": "0.10",
        "unit": "fração", "min_value": 0, "max_value": 2,
        "description": "Margem de segurança aplicada ao cenário conservador da estimativa condominial.",
    },
    {
        "key": "condominio.fator_otimista", "name": "Fator do cenário otimista",
        "category": "estimativa", "data_type": "DECIMAL", "value": "0.70", "default_value": "0.70",
        "unit": "fração", "min_value": 0, "max_value": 1,
        "description": "Fator aplicado ao cenário provável para compor o cenário otimista da estimativa condominial.",
    },
    # --- Alertas de idade (Etapa C) ---
    {
        "key": "checklist.idade_alerta_1_anos", "name": "Idade para alerta nível 1",
        "category": "alertas", "data_type": "INTEGER", "value": "10", "default_value": "10",
        "unit": "anos", "min_value": 0, "max_value": 200,
        "description": "Idade do imóvel (em anos) a partir da qual se emite alerta de atenção de manutenção/incerteza.",
    },
    {
        "key": "checklist.idade_alerta_2_anos", "name": "Idade para alerta nível 2",
        "category": "alertas", "data_type": "INTEGER", "value": "15", "default_value": "15",
        "unit": "anos", "min_value": 0, "max_value": 200,
        "description": "Idade do imóvel (em anos) a partir da qual o alerta de manutenção/incerteza é mais forte.",
    },
)


def seed_parameters(db: Session) -> int:
    """Materializa os parâmetros iniciais (idempotente por (key, scope GLOBAL)).

    Não sobrescreve valores já existentes (edições do operador são preservadas)."""
    created = 0
    for row in PARAMETER_SEED:
        exists = db.scalar(
            select(models.Parameter).where(
                models.Parameter.key == row["key"],
                models.Parameter.scope == "GLOBAL",
                models.Parameter.municipality_id.is_(None),
                models.Parameter.debt_category.is_(None),
            )
        )
        if exists is not None:
            continue
        db.add(models.Parameter(
            key=row["key"], name=row["name"], description=row.get("description"),
            category=row["category"], data_type=row["data_type"], scope="GLOBAL",
            value=row.get("value"), default_value=row.get("default_value"), unit=row.get("unit"),
            min_value=row.get("min_value"), max_value=row.get("max_value"),
            status="ATIVO", version=1, updated_by="seed",
        ))
        created += 1
    db.flush()
    return created

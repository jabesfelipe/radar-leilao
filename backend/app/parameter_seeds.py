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


# --- Premissas financeiras (v1.0.12, Admin > Premissas financeiras) -----------------------------------------------------
# Os valores vêm dos padrões já usados pelo motor de viabilidade (``viability.DEFAULTS``): o seed não muda nenhum cálculo,
# só torna a premissa visível e editável com histórico. Itens sem padrão do sistema (ITBI, IPTU, condomínio mensal,
# regularização, custos mensais) entram SEM valor: o motor continua tratando como pendente até o operador preencher.
# Precedência no cálculo: valor do imóvel > consulta/documento > estimativa calculada > este catálogo > pendente.
CATEGORIA_FINANCEIRO = "financeiro"
CATEGORIA_ESTIMATIVA = "estimativa"
_FINANCE_META: tuple[tuple[str, str, str, str | None, Any, Any], ...] = (
    # (chave, nome, categoria, unidade, mínimo, máximo) — valor e descrição vêm de viability.DEFAULTS
    ("venda.corretagem_pct", "Comissão de venda (corretagem)", CATEGORIA_FINANCEIRO, "fração", 0, 0.5),
    ("venda.tributo_ganho_pct", "Impostos na venda (IR sobre o ganho de capital)", CATEGORIA_FINANCEIRO, "fração", 0, 1),
    ("venda.prazo_meses", "Prazo até a revenda", CATEGORIA_FINANCEIRO, "meses", 1, 120),
    ("cenario.prazo_conservador_fator", "Multiplicador do prazo no cenário conservador", CATEGORIA_FINANCEIRO, "fator", 1, 5),
    ("cenario.prazo_otimista_fator", "Multiplicador do prazo no cenário otimista", CATEGORIA_FINANCEIRO, "fator", 0.1, 1),
    ("aluguel.taxa_ocupacao", "Ocupação média do imóvel alugado", CATEGORIA_FINANCEIRO, "fração", 0, 1),
    ("aluguel.taxa_administracao", "Taxa de administração da locação", CATEGORIA_FINANCEIRO, "fração", 0, 0.5),
    ("viabilidade.roi_minimo", "ROI mínimo (referência do preço máximo)", CATEGORIA_FINANCEIRO, "fração", 0, 5),
    ("viabilidade.reserva_registro_pct", "Escritura e registro (reserva)", CATEGORIA_FINANCEIRO, "fração", 0, 0.2),
    ("viabilidade.reserva_certidoes", "Certidões (reserva)", CATEGORIA_FINANCEIRO, "R$", 0, 100000),
    ("viabilidade.reserva_reforma_m2", "Reforma ampla (reserva do conservador)", CATEGORIA_FINANCEIRO, "R$/m²", 0, 20000),
    ("viabilidade.reserva_reforma_m2_base", "Manutenção e reparos leves (reserva do base)", CATEGORIA_FINANCEIRO, "R$/m²", 0, 20000),
    ("viabilidade.reserva_desocupacao", "Desocupação (reserva)", CATEGORIA_FINANCEIRO, "R$", 0, 1000000),
    ("checklist.reforma_grande_pct", "Referência de \"grande reforma\" no checklist", CATEGORIA_FINANCEIRO, "fração", 0, 1),
    ("mercado.desconto_negociacao", "Desconto de negociação sobre preço anunciado", "mercado", "fração", 0, 0.5),
    ("mercado.similaridade_minima", "Similaridade mínima do comparável", "mercado", "fração", 0, 1),
)
# Novos parâmetros (sem equivalente anterior no código). Valores documentados em docs/02-product/specs/INTELIGENCIA-IMOVEL.md.
_NEW_FINANCE: tuple[dict[str, Any], ...] = (
    {"key": "viabilidade.fator_venda_avaliacao", "name": "Fator de venda preliminar sobre a avaliação", "category": CATEGORIA_FINANCEIRO,
     "data_type": "DECIMAL", "value": "0.85", "unit": "fração", "min_value": 0.1, "max_value": 1.5,
     "description": "Valor de venda preliminar = avaliação do vendedor × fator, usado SÓ sem valor informado e sem comparáveis suficientes "
                    "(selo 'Estimativa preliminar', confiança Baixa)."},
    {"key": "viabilidade.margem_minima", "name": "Margem mínima (referência)", "category": CATEGORIA_FINANCEIRO, "data_type": "DECIMAL",
     "value": "0.10", "unit": "fração", "min_value": 0, "max_value": 1,
     "description": "Margem líquida (resultado ÷ venda) abaixo da qual a análise registra ressalva. Não substitui a meta do investidor."},
    {"key": "viabilidade.margem_seguranca_minima", "name": "Margem de segurança mínima (referência)", "category": CATEGORIA_FINANCEIRO,
     "data_type": "DECIMAL", "value": "0.10", "unit": "fração", "min_value": 0, "max_value": 1,
     "description": "Margem de segurança (1 − venda de equilíbrio ÷ venda) abaixo da qual a análise registra ressalva."},
    {"key": "viabilidade.itbi_aliquota", "name": "ITBI (alíquota)", "category": CATEGORIA_FINANCEIRO, "data_type": "DECIMAL", "value": None,
     "unit": "fração", "min_value": 0, "max_value": 0.2,
     "description": "Alíquota do ITBI. Sem valor padrão: cadastre a alíquota com fonte oficial, de preferência por município (escopo MUNICIPIO)."},
    {"key": "viabilidade.regularizacao_padrao", "name": "Regularização (reserva padrão)", "category": CATEGORIA_FINANCEIRO, "data_type": "DECIMAL",
     "value": None, "unit": "R$", "min_value": 0, "max_value": 1000000,
     "description": "Reserva de regularização usada quando o imóvel não tem levantamento próprio. Sem valor padrão."},
    {"key": "iptu.valor_anual_padrao", "name": "IPTU anual padrão", "category": CATEGORIA_FINANCEIRO, "data_type": "DECIMAL", "value": None,
     "unit": "R$/ano", "min_value": 0, "max_value": 1000000,
     "description": "IPTU anual de referência durante a posse, quando não há carnê, certidão ou consulta. Sem valor padrão."},
    {"key": "viabilidade.custos_mensais_padrao", "name": "Custos mensais da posse (padrão)", "category": CATEGORIA_FINANCEIRO,
     "data_type": "DECIMAL", "value": None, "unit": "R$/mês", "min_value": 0, "max_value": 100000,
     "description": "Custo mensal de manutenção da posse (condomínio e despesas) quando não informado e sem comparáveis. Sem valor padrão."},
    {"key": "condominio.valor_mensal_referencia", "name": "Condomínio mensal padrão", "category": CATEGORIA_ESTIMATIVA, "data_type": "DECIMAL",
     "value": None, "unit": "R$/mês", "min_value": 0, "max_value": 100000,
     "description": "Taxa condominial mensal de referência da estimativa condominial, quando não informada e sem comparáveis. Sem valor padrão."},
    # Estimativa condominial (Fase E): cenários sobre o período entre a aquisição e a consolidação (que NÃO prova inadimplência).
    {"key": "condominio.fator_cenario_baixo", "name": "Estimativa condominial: cenário baixo", "category": CATEGORIA_ESTIMATIVA,
     "data_type": "DECIMAL", "value": "0.15", "unit": "fração do período", "min_value": 0, "max_value": 1,
     "description": "Fração do período considerado (aquisição → consolidação, com teto) presumida em atraso no cenário baixo."},
    {"key": "condominio.fator_cenario_provavel", "name": "Estimativa condominial: cenário provável", "category": CATEGORIA_ESTIMATIVA,
     "data_type": "DECIMAL", "value": "0.35", "unit": "fração do período", "min_value": 0, "max_value": 1,
     "description": "Fração do período considerado presumida em atraso no cenário provável (usado no cenário financeiro base)."},
    {"key": "condominio.fator_cenario_alto", "name": "Estimativa condominial: cenário alto", "category": CATEGORIA_ESTIMATIVA,
     "data_type": "DECIMAL", "value": "0.70", "unit": "fração do período", "min_value": 0, "max_value": 1,
     "description": "Fração do período considerado presumida em atraso no cenário alto (usado no cenário financeiro conservador)."},
    {"key": "condominio.periodo_maximo_meses", "name": "Estimativa condominial: teto do período", "category": CATEGORIA_ESTIMATIVA,
     "data_type": "INTEGER", "value": "60", "unit": "meses", "min_value": 1, "max_value": 240,
     "description": "Teto do período considerado na estimativa. Padrão de 60 meses: prazo de prescrição da cobrança de cotas "
                    "condominiais (5 anos, Código Civil art. 206, § 5º, I, conforme o STJ)."},
    {"key": "condominio.juros_mensal_pct", "name": "Estimativa condominial: juros de mora", "category": CATEGORIA_ESTIMATIVA,
     "data_type": "DECIMAL", "value": "0.01", "unit": "fração ao mês", "min_value": 0, "max_value": 0.2,
     "description": "Juros de mora mensais simples sobre cada cota em atraso (Código Civil art. 1.336, § 1º: 1% ao mês se a convenção não dispuser)."},
    {"key": "condominio.multa_pct", "name": "Estimativa condominial: multa", "category": CATEGORIA_ESTIMATIVA, "data_type": "DECIMAL",
     "value": "0.02", "unit": "fração", "min_value": 0, "max_value": 0.2,
     "description": "Multa sobre cada cota em atraso (Código Civil art. 1.336, § 1º: até 2%)."},
    {"key": "condominio.correcao_mensal_pct", "name": "Estimativa condominial: correção monetária", "category": CATEGORIA_ESTIMATIVA,
     "data_type": "DECIMAL", "value": "0.004", "unit": "fração ao mês", "min_value": 0, "max_value": 0.1,
     "description": "Correção monetária mensal simples de referência (≈ 4,9% ao ano). Ajuste ao índice da convenção (ex.: IPCA, INPC)."},
)


def _finance_seed() -> tuple[dict[str, Any], ...]:
    from .viability import DEFAULTS   # import local: viability não depende deste módulo
    rows = []
    for key, name, category, unit, min_value, max_value in _FINANCE_META:
        value, label = DEFAULTS[key]
        data_type = "INTEGER" if isinstance(value, int) else "DECIMAL"
        rows.append({"key": key, "name": name, "category": category, "data_type": data_type, "value": str(value), "default_value": str(value),
                     "unit": unit, "min_value": min_value, "max_value": max_value, "description": label})
    return tuple(rows) + tuple({**row, "default_value": row.get("value")} for row in _NEW_FINANCE)


def all_parameter_seeds() -> tuple[dict[str, Any], ...]:
    return PARAMETER_SEED + _finance_seed()


def seed_parameters(db: Session) -> int:
    """Materializa os parâmetros iniciais (idempotente por (key, scope GLOBAL)).

    Não sobrescreve valores já existentes (edições do operador são preservadas)."""
    created = 0
    for row in all_parameter_seeds():
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

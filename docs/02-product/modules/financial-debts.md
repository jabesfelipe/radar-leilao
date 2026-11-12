# Financeiro e Central de Débitos

**Status: implementado** (cenário BASE; OTIMISTA/PESSIMISTA, TIR/VPL e sensibilidade planejados). Consulta de débitos: provider manual-assistido.

## Objetivo
Calcular custo total, resultado, margem, ROI e preço máximo do lance, e consolidar débitos e despesas do imóvel.

## Funcionalidades
- Motor determinístico `finance.py`: custos por categoria sem dupla contagem, deságio, margem, yield, custos de saída (corretagem e tributo, base GANHO ou VENDA), resultado líquido, ROI da operação, break-even, preço máximo por meta (LUCRO_MINIMO, MARGEM_MINIMA, ROI_MINIMO), carregamento mensal × prazo. Detalhes em [evaluation-criteria.md](../../01-business/evaluation-criteria.md#4-análise-financeira).
- ITBI e registro **não são calculados**: custo informado; ausente vira DESCONHECIDO e o resultado fica provisório.
- Premissas financeiras editáveis; análises financeiras versionadas (V1 a V9 no imóvel de referência).
- Custos do imóvel (CRUD com histórico).
- Central de Débitos: débitos normalizados, consolidação por natureza (confirmados, informados, estimados, despesas previstas), estimativa condominial com 3 cenários (sempre ESTIMADO), histórico de consultas de débito.
- Catálogos administráveis: municípios, tipos de débito, fontes e matriz de cobertura (ver [administration.md](administration.md)).

## Telas
Hub `/financeiro`; no imóvel: "Financeiro" e "Débitos".

## Endpoints
`GET /api/imoveis/{id}/financeiro`, `GET/PUT .../financeiro/premissas`, `POST .../financeiro/analisar`; `GET/POST/PATCH/DELETE /api/imoveis/{id}/custos`; débitos: `GET/POST /api/imoveis/{id}/debitos`, `GET/PATCH .../{debt_id}`, `GET .../consolidacao`, `GET .../consultas`, `POST .../consultar`, `GET .../estimativas-condominio`, `POST .../estimar-condominio`; hub `GET /api/financeiro`.

## Integrações
`debt_providers.py`: apenas manual-assistido. Sem integração automática com prefeituras ou administradoras.

## Limitações e divergências
- Categorias de custo fixas; sem parametrização fiscal por jurisdição, ato e vigência ([MATRIZ-CUSTOS-TRIBUTOS-EMOLUMENTOS](../specs/MATRIZ-CUSTOS-TRIBUTOS-EMOLUMENTOS.md)).
- Sem TIR, VPL, fluxo descontado nem grid de sensibilidade.
- Comentário em `backend/app/models.py` cita o plano antigo `PLAN-CENTRAL-DEBITOS-DESPESAS-ADMIN` (ver [99-archive](../../99-archive/README.md)).

## Código
`finance.py`, `estimates_service.py`, `debts_service.py`, `debt_providers.py`, `debt_query_service.py`, `routers/debts.py`, `impact.py`.

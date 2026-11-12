# Dashboard e hubs

**Status: implementado.**

## Objetivo
Dar visão consolidada do portfólio: painel de decisão e listagens agregadas por tema (financeiro, jurídico, riscos, veredito, mercado, ocupação, documentos, histórico, checklist).

## Telas (frontend)
- `/dashboard`: DashboardHub (KPIs, pipeline, alertas calculados a partir dos dados reais).
- `/oportunidades`: painel do pipeline de oportunidades (ver [opportunities-workflow.md](opportunities-workflow.md)).
- Hubs: `/documentos`, `/juridico`, `/financeiro`, `/mercado`, `/ocupacao`, `/checklist`, `/riscos`, `/veredito`, `/historico`.
- Sidebar com 14 itens; rota desconhecida cai em `/dashboard`.

## Endpoints
`routers/hubs.py` (sem JWT): `GET /api/dashboard`, `/api/imoveis-resumo`, `/api/financeiro`, `/api/juridico`, `/api/riscos` (filtro `severity`), `/api/veredito`, `/api/mercado`, `/api/ocupacao`, `/api/documentos` (filtro `doc_type`), `/api/historico`, `/api/checklist-global`.
`routers/dashboard.py`: `GET /api/dashboard/oportunidades` (exige JWT).

## Dados
Somente leitura sobre `Property`, `Risk`, análises e demais tabelas; nada próprio.

## Regras
Os valores exibidos (preço máximo, ROI, risco, veredito) vêm dos motores; o hub não recalcula regras.

## Permissões
Hubs sob `/api/*` legados não exigem JWT no backend; o portão do proxy é a barreira de borda. O painel de oportunidades exige JWT.

## Limitações
Hub e rota de dashboard coexistem (`/api/dashboard` e `/api/dashboard/oportunidades`).

## Código
`backend/app/routers/hubs.py`, `routers/dashboard.py`; `frontend/src/pages` (DashboardHub e hubs), `frontend/src/App.tsx`.

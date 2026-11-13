# Checklist, riscos, veredito e análise

**Status: implementado.** Agentes de IA exigem `OPENAI_API_KEY`; sem ela o resultado é `SEM_CHAVE`.

## Objetivo
Estruturar a verificação do método (checklist), transformar achados em riscos e sintetizar um veredito explicável, com versões de análise.

## Funcionalidades
- **Checklist mestre** de 27 itens, editável (criar, alterar, ativar, desativar, histórico) e executado por imóvel, com resultados versionados por execução. Ver [evaluation-criteria.md](../../01-business/evaluation-criteria.md#1-checklist-mestre).
- **Riscos** (`risk_engine.py`): RISCO_IDENTIFICADO gera ALTA, ATENCAO gera MEDIA, apenas com evidência.
- **Veredito** (`verdict_engine.py`): DESFAVORAVEL, ATENCAO, INCONCLUSIVO ou FAVORAVEL.
- **Análises versionadas**: `POST /api/imoveis/{id}/analisar` executa o grafo LOAD_CONTEXT, RETRIEVE_RAG, RUN_AGENTS, CONSOLIDATE (LangGraph); agentes documental, jurídico, financeiro, mercado e checklist.
- Comparação entre análises, reconciliação e impacto (`analysis_comparison.py`, `reconciliation.py`, `impact.py`), memória de conhecimento (`knowledge_memory.py`).
- Registro de cada chamada de LLM em `llm_runs` (45 no imóvel de referência).

## Telas
Hubs `/checklist`, `/riscos`, `/veredito`, `/historico`; seções homônimas no imóvel.

## Endpoints
`/api/checklist` (GET/POST, `/{id}` GET/PATCH, `/{id}/ativar`, `/{id}/desativar`, `/{id}/historico`); `GET /api/imoveis/{id}/checklist` e `/checklist/historico`; `POST /api/imoveis/{id}/analisar` (corpo opcional: até 5 `domains` válidos e `query` de até 500 caracteres, senão 422; ver [security.md](../../03-architecture/security.md#contrato-de-post-apiimoveisidanalisar)); `POST /api/imoveis/{id}/analises/{aid}/agents/{documental|juridico|financeiro|mercado|checklist}`; hubs `/api/riscos`, `/api/veredito`, `/api/checklist-global`.

## Estados
Checklist: PENDENTE, EM_ANALISE, CONFIRMADO, RISCO_IDENTIFICADO, ATENCAO, NAO_IDENTIFICADO, NAO_APLICAVEL (7). Confiança: BAIXA, MEDIA, ALTA.

## Divergências
- Chave `COMPARAVEIS_SUFFICIENTES` com erro de grafia (preservada por ser chave canônica).
- `MATRIZ-CHECKLIST-MODALIDADE` afirma "nada implementado", mas a aplicabilidade existe em `modality_rules.py`.

## Código
`checklist.py`, `risk_engine.py`, `verdict_engine.py`, `ai/` (agentes e grafo), `services.py`, `evidence.py`, `incremental.py`.

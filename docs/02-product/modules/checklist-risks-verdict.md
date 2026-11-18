# Checklist, riscos, veredito e análise

**Status: implementado.** Agentes de IA exigem `OPENAI_API_KEY`; sem ela o resultado é `SEM_CHAVE`.

## Objetivo
Estruturar a verificação do método (checklist), transformar achados em riscos e sintetizar um veredito explicável, com versões de análise.

## Funcionalidades
- **Checklist mestre** de 27 itens, editável (criar, alterar, ativar, desativar, histórico) e executado por imóvel, com resultados versionados por execução. Ver [evaluation-criteria.md](../../01-business/evaluation-criteria.md#1-checklist-mestre).
- **Aplicabilidade por modalidade** (`modality_rules.py`, ruleset `modality-v2`): decidida pela finalidade de cada item; cada resultado guarda status, justificativa e a regra `modality-v2:<MODALIDADE>:<chave>`. Item condicional continua PENDENTE (nunca vira resposta). Tabela da venda direta em [MATRIZ-CHECKLIST-MODALIDADE](../specs/MATRIZ-CHECKLIST-MODALIDADE.md#regra-implementada-para-venda_direta-modality-v2).
- **Itens respondidos pela cadeia registral** (sem IA, com os trechos da matrícula vinculados): CONSOLIDACAO_REGISTRADA (alienação + consolidação → CONFIRMADO; só alienação → INCONCLUSIVO) e PENHORA_INDISPONIBILIDADE (penhora/indisponibilidade encontrada → RISCO_IDENTIFICADO). RESPONSABILIDADE_DEBITOS fica INCONCLUSIVO com as condições da venda informadas nas premissas, até o documento ser anexado.
- **Classificação por evidências** (`checklist_evidence.py`, regra `evidencias-v1`, v1.0.11): fonte única no backend que usa a matrícula (itens 1–5, 7, 8, 10–12, 16), as condições oficiais da venda (14 e 15, documento `CONDICOES_VENDA` ou edital; `sale_conditions.py`) e os módulos de ocupação, processos, localização, mercado e premissas (7, 11, 17–27). Item jurídico só é CONFIRMADO com trecho do documento; "sem restrição identificada" (NAO_IDENTIFICADO) exige a matrícula lida em sequência contínua de atos e não é garantia de inexistência; item pendente recebe justificativa própria e a ação. Tabela por item em [MATRIZ-CHECKLIST-MODALIDADE](../specs/MATRIZ-CHECKLIST-MODALIDADE.md#classificação-por-evidências-evidencias-v1-v1011) e fluxo em [checklist-evidencias.md](../../03-architecture/checklist-evidencias.md).
- **Resultado e evidências na tela**: cada item mostra o resultado (Comprovado, Risco identificado, Pendente, Inconclusivo, Não aplicável, Sem restrição identificada), a conclusão, a fundamentação, o que fazer e a fonte necessária; "Ver evidências" abre documento, página, trecho original, tipo (fato documental, regra oficial da venda, cálculo, inferência da IA, informação do usuário, informação não localizada), confiança, responsável e data.
- **Riscos** (`risk_engine.py`): RISCO_IDENTIFICADO gera ALTA, ATENCAO gera MEDIA, apenas com evidência.
- **Veredito** (`verdict_engine.py`): DESFAVORAVEL, ATENCAO, INCONCLUSIVO ou FAVORAVEL. Os fatores (`decisao.fatores`) separam impedimentos, informações essenciais desconhecidas, premissas não configuradas, riscos que reduzem a confiança e não aplicáveis, com justificativa e ação; um risco gerado de item do checklist aparece uma vez só. O financeiro do veredito usa a composição única ([financial-debts.md](financial-debts.md)).
- **Análises versionadas**: `POST /api/imoveis/{id}/analisar` executa o grafo LOAD_CONTEXT, RETRIEVE_RAG, RUN_AGENTS, CONSOLIDATE (LangGraph); agentes documental, jurídico, financeiro, mercado e checklist.
- Comparação entre análises, reconciliação e impacto (`analysis_comparison.py`, `reconciliation.py`, `impact.py`), memória de conhecimento (`knowledge_memory.py`).
- Registro de cada chamada de LLM em `llm_runs` (45 no imóvel de referência).

## Telas
Hubs `/checklist`, `/riscos`, `/veredito`, `/historico`; seções homônimas no imóvel.

## Endpoints
`/api/checklist` (GET/POST, `/{id}` GET/PATCH, `/{id}/ativar`, `/{id}/desativar`, `/{id}/historico`); `GET /api/imoveis/{id}/checklist` (cada resultado traz também `question` adequada à modalidade, `resultado`, `resultado_label`, `acao_recomendada`, `fonte_necessaria`) e `/checklist/historico`; `GET /api/imoveis/{id}/checklist/{resultado_id}/evidencias` (v1.0.11); `POST /api/imoveis/{id}/analisar` (corpo opcional: até 5 `domains` válidos e `query` de até 500 caracteres, senão 422; ver [security.md](../../03-architecture/security.md#contrato-de-post-apiimoveisidanalisar)); `POST /api/imoveis/{id}/analises/{aid}/agents/{documental|juridico|financeiro|mercado|checklist}`; hubs `/api/riscos`, `/api/veredito`, `/api/checklist-global`.

## Estados
Checklist: PENDENTE, EM_ANALISE, CONFIRMADO, RISCO_IDENTIFICADO, ATENCAO, NAO_IDENTIFICADO, NAO_APLICAVEL (7, gravados; sem mudança). Confiança: BAIXA, MEDIA, ALTA. Resultado para o investidor (derivado, v1.0.11): CONFIRMADO, RISCO_IDENTIFICADO (inclui ATENCAO), PENDENTE, INCONCLUSIVO (EM_ANALISE), NAO_APLICAVEL, SEM_RESTRICAO_IDENTIFICADA (NAO_IDENTIFICADO).

## Divergências
- Chave `COMPARAVEIS_SUFFICIENTES` com erro de grafia (preservada por ser chave canônica).
- Vereditos anteriores à v2 não têm `fatores`; a tela mostra os fundamentos.

## Código
`checklist.py`, `checklist_evidence.py`, `sale_conditions.py`, `registry_chain.py`, `risk_engine.py`, `verdict_engine.py`, `ai/` (agentes e grafo), `services.py`, `evidence.py`, `incremental.py`.

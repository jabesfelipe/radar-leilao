# RADAR LEILÃO — STATUS DO PROJETO

**Status global: MVP ENCERRADO (núcleo funcional) — validação operacional incremental pendente**

**Última atualização:** 25/09/2026  
**Última implementação:** Task 68 — commit b3a94f59f35ffb9ad546a0400dc57b05b3f817ae

## 1. Resumo executivo

O MVP do Radar Leilão está encerrado tecnicamente.

O fluxo principal foi implementado em Python/FastAPI + React/TypeScript, com PostgreSQL/pgvector, processamento documental com MarkItDown/OCR, RAG híbrido, LangChain/LangGraph, cinco agentes LLM especializados, Checklist Mestre, Risk Engine, Verdict Engine, histórico e memória estruturada.

A validação final utilizou o imóvel real COND PARQUE ARVOREDO RESIDENCIAL CLUBE, referência Caixa, e chegou à análise V8 (analysis_id=280).

## 2. Estado final por capacidade

| Capacidade | Estado | Observação |
|---|---|---|
| Fundação / arquitetura | OK | Python + FastAPI + React + PostgreSQL/pgvector |
| Cadastro do imóvel/leilão | OK | Fluxo completo implementado |
| Documentos | OK | Upload, versionamento e rastreabilidade |
| MarkItDown | OK | Normalização documental |
| OCR | OK | Tesseract + Poppler operacional no Docker |
| Embeddings | OK | Gerados na ingestão quando provider/chave disponíveis |
| RAG híbrido | OK | Vetor + texto + filtros |
| RAG direcionado do Checklist | OK | 4 por item / 24 distintos + diversidade por documento |
| Agentes LLM | OK | Documental, Jurídico, Financeiro, Mercado, Checklist |
| LangGraph | OK | Orquestração do fluxo |
| Checklist Mestre | OK | 27 canonical keys de referência, versionado |
| Financeiro | OK | Motor determinístico |
| Mercado | OK | Motor determinístico + agente interpretativo |
| Ocupação/Desocupação | OK | Domínio funcional; sem agente LLM separado |
| Processos | OK | Cadastro e movimentações |
| Evidências | OK | Rastreáveis por documento/versão/chunk |
| Risk Engine | OK | Persistência e versionamento |
| Verdict Engine | OK | Veredito explicável/rastreável |
| Histórico | OK | Análises, eventos e versões |
| Memória histórica | OK | Estruturada + busca híbrida |
| Frontend | OK | Hubs do fluxo principal |
| E2E real Caixa | OK | V8 executada com 5 agentes |
| Testes backend | OK | 258 passed |
| MCP externo | FUTURO | Não é dependência do MVP |
| Knowledge Graph dedicado | FUTURO | Não implementado como componente dedicado |
| Redis | FUTURO | Não utilizado no MVP |
| S3/MinIO | FUTURO | Storage atual é filesystem persistente |
| Leilão judicial | FORA DO ESCOPO | Não implementado |

## 3. E2E final

Imóvel: COND PARQUE ARVOREDO RESIDENCIAL CLUBE — Caixa — Curitiba/PR

V8:
- analysis_id=280;
- 5/5 agentes CONCLUIDO;
- gpt-4o-mini;
- 35.231 tokens;
- custo aproximado: US$ 0,0072;
- 7 CONFIRMADO / 20 PENDENTE;
- Veredito INCONCLUSIVO;
- V1–V8 preservadas.

Distribuição de contexto:

| Agente | Edital | Matrícula |
|---|---:|---:|
| Checklist | 22 | 2 |
| Documental | 7 | 1 |
| Jurídico | 7 | 1 |
| Financeiro | 7 | 1 |
| Mercado | 7 | 1 |

## 4. Última correção funcional

Task 68 corrigiu a ausência artificial do edital no contexto RAG.

- edital doc 193 → v2 / document_version_id=474;
- 544 chunks;
- 544 embeddings;
- dimensão 1536;
- v1 preservada;
- sem backfill global;
- diversidade por documento no retrieval direcionado;
- proteção contra chunk_id fora do range int4.

Resultado:

24 edital / 0 matrícula → 22 edital / 2 matrícula.

## 5. Testes

Último resultado registrado:

    pytest -q
    258 passed

Não há afirmação de CI/CD ou homologação produtiva baseada somente nesse resultado.

## 6. Limitações / backlog

- Refinamento futuro do retrieval por item para casos de forte similaridade semântica entre documentos.
- Embedding do doc 195 duplicado, se algum fluxo futuro precisar especificamente dessa versão/origem.
- Integrações externas e pesquisa jurídica automática.
- MCP e ferramentas externas.
- Knowledge Graph dedicado.
- S3/MinIO.
- Redis, somente se houver necessidade real.
- Suporte a leilão judicial.
- Evolução de avaliações/evals com conjunto maior de imóveis reais.
- Hardening e requisitos de produção, caso o projeto deixe de ser local/MVP.

## 7. Regra para continuidade

Para qualquer retomada futura, consultar nesta ordem:

1. docs/SPEC-VIBE-CODING-RADAR-LEILAO.md
2. docs/PROJECT-STATUS.md
3. docs/PROJECT-HISTORY.md
4. código + testes

A documentação deve ser atualizada junto com qualquer mudança arquitetural futura.

## 8. Encerramento

**MVP ENCERRADO — 25/09/2026**

O núcleo funcional do MVP permanece encerrado. A validação E2E real V1–V8 foi concluída e o código atual preserva o serviço de reanálise incremental.

### 8.1 Follow-up operacional de validação

Durante a preparação do teste de reanálise, foi confirmado que:

- `backend/app/incremental.py` implementa `IncrementalAnalysisService.run_for_event()`;
- `ImpactAnalyzer` decide se o evento exige reanálise e quais domínios são afetados;
- o serviço cria nova versão de `Analysis`, executa o orquestrador nos domínios afetados, persiste evidências/LLM usage/riscos/veredito e marca o evento como processado;
- existem testes unitários específicos para esse serviço;
- não foi encontrado, no código atual, um endpoint/worker operacional que invoque `run_for_event()`.

Portanto, a próxima ação é **exclusivamente habilitar o gatilho operacional desse serviço para permitir a validação real V8 → V9**. Isso não reabre o núcleo funcional do MVP nem altera arquitetura, RAG, agentes, Checklist ou regras de negócio.

A tarefa de continuidade fica registrada como **Task 69 — Gatilho operacional da reanálise incremental**, com escopo estritamente limitado à exposição do serviço já implementado.

Novas funcionalidades fora desse objetivo continuam sendo evolução/backlog.

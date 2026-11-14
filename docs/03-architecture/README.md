# 03 — Arquitetura

| Documento | Conteúdo |
|---|---|
| [architecture.md](architecture.md) | visão geral e **11 diagramas** (contexto, containers, backend, frontend, persistência, autenticação, workflow, financeiro, documental/jurídico, integrações, infra/deploy) |
| [data-model.md](data-model.md) | grupos de tabelas, migrations 0001 a 0024, invariantes |
| [integrations.md](integrations.md) | estado de cada integração (existe, opcional, sem cliente) |
| [security.md](security.md) | autenticação, perfis, rotas públicas e críticas, limites, uploads, erros, concorrência, OpenAI, homologação e rollback |
| [decisions/README.md](decisions/README.md) | índice de ADRs, só com evidência |

## Especificações técnicas (`specs/`)

Mantidas como referência de domínio; onde o texto diverge do código, vale o código e os documentos acima.

| Especificação | Situação |
|---|---|
| [SPEC-RADAR-LEILAO-INTELLIGENCE](specs/SPEC-RADAR-LEILAO-INTELLIGENCE.md) | proposta para MVP; módulo independente, coleta condicionada à validação de conformidade |
| [SPEC-WORKFLOW-ENGINE](specs/SPEC-WORKFLOW-ENGINE.md) | válida; implementada em `workflow_rules.py` e `workflow_engine.py` |
| [SPEC-HARD-STOPS](specs/SPEC-HARD-STOPS.md) | válida |
| [SPEC-INVALIDATION-STRATEGY](specs/SPEC-INVALIDATION-STRATEGY.md) | válida |
| [SPEC-OPPORTUNITY-DOMAIN](specs/SPEC-OPPORTUNITY-DOMAIN.md) | válida |
| [SPEC-OPPORTUNITY-ISOLATION](specs/SPEC-OPPORTUNITY-ISOLATION.md) | válida |
| [MODEL-DATA-WORKFLOW](specs/MODEL-DATA-WORKFLOW.md) | válida |
| [MATRIZ-OPPORTUNITY-ID](specs/MATRIZ-OPPORTUNITY-ID.md) | válida |
| [RAG-ARCHITECTURE](specs/RAG-ARCHITECTURE.md), [RAG-LIFECYCLE](specs/RAG-LIFECYCLE.md) | válidas |
| [SECURITY-EXPOSURE-AUDIT](specs/SECURITY-EXPOSURE-AUDIT.md) | válida como auditoria; ver [security.md](security.md) para o estado atual |
| [JUDICIAL-API-SPEC](specs/JUDICIAL-API-SPEC.md) | válida (2570 linhas); módulo `judicial_api/` |
| [SPEC-ADAPTADORES-CONSULTA-MUNICIPAL](specs/SPEC-ADAPTADORES-CONSULTA-MUNICIPAL.md) | planejada; sem cliente implementado |
| [decisions/ADR-WORKFLOW-ARCHITECTURE](decisions/ADR-WORKFLOW-ARCHITECTURE.md) | em vigor; status formal "PROPOSTO" no original (banner explica) |

## Nota sobre referências internas

Os textos em `specs/` e `decisions/` foram preservados sem edição de conteúdo (exceto banners de status). Referências do tipo `docs/NOME.md` dentro deles
usam os caminhos anteriores; o destino atual de cada documento está no inventário em [../README.md](../README.md#inventário-e-classificação-79-documentos).

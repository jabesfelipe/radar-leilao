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

---

## TASK 69 — Execução: gatilho operacional da reanálise incremental

- [x] CONCLUÍDA (aguardando auditoria)
- **Endpoint novo:** `POST /api/imoveis/{property_id}/eventos/{event_id}/reanalisar` (`reanalyze_from_event` em `backend/app/main.py`). Valida o imóvel (`property_or_404`), busca o `DomainEvent` e confirma que ele pertence ao imóvel (404 caso não exista ou seja de outro imóvel), então **delega** a `IncrementalAnalysisService(db).run_for_event(event)` e retorna o resultado do serviço. Em erro, responde 502 preservando o rollback transacional que o próprio serviço já faz.
- **Sem lógica nova:** o endpoint é apenas o gatilho de runtime. Nenhuma alteração em `IncrementalAnalysisService`, `ImpactAnalyzer`, LangGraph, RAG, Checklist, agentes, Risk/Verdict. Sem migration, sem mudança de modelos, sem nova arquitetura. Se `requires_reanalysis=False`, o serviço retorna `analise_executada=False` sem criar nova Analysis.
- **Testes:** `tests/test_reanalyze_endpoint.py` (5) — evento inexistente → 404; evento de outro imóvel → 404; imóvel inexistente → 404; evento sem reanálise → `analise_executada=False` e nenhuma Analysis criada pelo endpoint; evento com reanálise (serviço mockado, sem LLM) → `run_for_event` chamado e `analysis_id`/versão preservados no response. `pytest -q` = **263 passed** (258 anteriores + 5 novos), sem regressão.
- Permite o teste operacional manual (pós-auditoria): `V8 → DomainEvent → ImpactAnalyzer → reanálise incremental → V9`, preservando o histórico.

**Status global (Task 69):** 🟢 suíte verde (263 passed); gatilho operacional da reanálise incremental exposto por endpoint que delega ao serviço existente; nenhuma lógica de análise duplicada ou alterada.

---

## 9. Validação pela UI — descoberta de inconsistências

**Atualização: 25/09/2026 — validação manual pelo usuário**

A validação do imóvel real **COND PARQUE ARVOREDO RESIDENCIAL CLUBE (property_id=633)** passou a ser conduzida pela interface do Radar, como usuário final.

Na tela do Dossiê foi confirmado:

- imóvel acessível pela rota `/imoveis/633`;
- aba **Documentos** funcional;
- matrícula com 3 versões processadas;
- edital principal `EL00440226CPARE.pdf` com 2 versões processadas;
- histórico exibindo a Análise V8;
- Checklist exibindo **7 CONFIRMADOS / 20 PENDENTES**.

### 9.1 Bug funcional identificado — Veredito selecionava versão antiga

Na aba **Veredito**, a UI exibiu:

- `Analysis V7`;
- 28 pendências;

enquanto o histórico já possui a **V8** e o Checklist da V8 possui 7 itens confirmados.

A causa foi localizada no endpoint `GET /api/imoveis/{property_id}`:

```python
latest = prop.verdicts[-1] if prop.verdicts else None
```

O relacionamento `prop.verdicts` não possui ordenação explícita por `analysis_version`. Portanto, usar `[-1]` não garante que o último elemento seja o Veredito da análise mais recente.

A correção planejada é selecionar explicitamente o maior `analysis_version`, com desempate por `id`:

```python
latest = db.scalar(
    select(models.Verdict)
    .where(models.Verdict.property_id == property_id)
    .order_by(
        models.Verdict.analysis_version.desc(),
        models.Verdict.id.desc()
    )
)
```

### 9.2 Bug de usabilidade — evidências exibidas somente como IDs internos

Na mesma tela, **Evidências vinculadas** apareciam como valores do tipo:

```text
#202, #203, #204, ...
```

Esses números são IDs internos de banco e não são informação útil para um usuário leigo.

A apresentação esperada deve ser derivada dos dados reais de `Evidence`, `DocumentVersion` e `DocumentChunk`, quando disponíveis, exibindo:

- documento;
- tipo/categoria;
- versão;
- página/seção, quando disponível;
- trecho/descrição da evidência, quando disponível;
- rastreamento até a fonte, sem expor o ID interno como informação principal.

**Não inventar descrições ou páginas.** Quando os metadados não existirem, utilizar uma descrição conservadora.

### 9.3 Task 70 — correção de seleção do Veredito + evidências legíveis

A Task 70 fica registrada como a próxima tarefa de correção funcional:

1. selecionar deterministicamente o Veredito da maior `analysis_version`;
2. criar teste de regressão V7/V8 para o endpoint de imóvel;
3. transformar IDs de evidência em apresentação legível no Veredito;
4. preservar `evidence_id` internamente para rastreabilidade;
5. validar a suíte completa sem executar nova análise real do imóvel 633.

**Status:** 🟡 especificada, aguardando implementação/auditoria.

### 9.4 Regra de validação após a Task 70

```text
rebuild / health
    ↓
abrir /imoveis/633
    ↓
Veredito
    ↓
confirmar Analysis V8
    ↓
confirmar 7 CONFIRMADOS / 20 PENDENTES
    ↓
confirmar evidências legíveis
    ↓
somente depois retomar validação incremental V8 → V9
```

A Task 70 **não deve gerar V9** e não deve alterar os dados reais do imóvel 633 durante os testes automatizados.


---

## 10. TASK 70 — Veredito e evidências na UI

**Commit:** `7f8f62454288b96723ea15909c0c967dfbcae3d2`  
**Status:** 🟢 APROVADA POR AUDITORIA — 25/09/2026

Correções confirmadas:

- `GET /api/imoveis/{property_id}` seleciona o Veredito por `analysis_version DESC, id DESC`;
- elimina a dependência de `prop.verdicts[-1]`;
- imóvel 633 passa a apontar deterministicamente para a V8;
- nova visão `veredito_evidencias` resolve as evidências reais a partir dos IDs do Veredito;
- UI passa a mostrar documento, categoria, versão, página/seção e fato/trecho quando disponíveis;
- campos ausentes são omitidos, sem invenção de metadados;
- `veredito.evidence_ids` permanece preservado para rastreabilidade;
- fallback visual para IDs existe somente quando a visão legível não estiver disponível.

### Validação automatizada

Backend:

```text
pytest -q
267 passed
0 falhas
```

Frontend:

```text
Vitest: 90 passed
TypeScript: tsc --noEmit OK
```

### Escopo auditado

Não houve alteração em:

- Verdict Engine;
- Risk Engine;
- RAG;
- LangGraph;
- agentes;
- Checklist;
- modelos/migrations;
- IncrementalAnalysisService;
- ImpactAnalyzer.

Também não houve nova análise real nem geração de V9.

### Próximo marco

A Task 70 encerra as correções necessárias identificadas na validação visual do imóvel 633.

Próxima etapa, após rebuild/health e validação manual da tela:

```text
UI imóvel 633
    ↓
Veredito = V8
    ↓
evidências legíveis
    ↓
validar gatilho operacional
    ↓
V8 → DomainEvent → ImpactAnalyzer
    ↓
reanálise incremental
    ↓
V9
```


## 11. TASK 71 — Correção da seleção da execução do Checklist usada pelo Veredito

**Status:** 🟡 especificada — aguardando implementação/auditoria

Diagnóstico confirmado no imóvel 633: a execução V8 do Checklist possui **27 resultados, 7 CONFIRMADO e 20 PENDENTE**. O Veredito V8 persistido possui **28 pending_items** porque recebeu as 27 perguntas do Checklist como pendentes, inclusive as 7 confirmadas, mais uma pendência financeira legítima sobre a fórmula canônica de preço máximo.

A causa está em backend/app/services.py:

    def latest_execution(prop: models.Property):
        return next(iter(reversed(prop.checklist_executions)), None)

A seleção depende da ordem incidental do relacionamento ORM, e não de analysis_version.

A Task 71 deve corrigir isso de forma determinística:

    return db.scalar(
        select(models.ChecklistExecution)
        .where(models.ChecklistExecution.property_id == prop.id)
        .order_by(
            models.ChecklistExecution.analysis_version.desc(),
            models.ChecklistExecution.id.desc(),
        )
    )

### Escopo fechado

- corrigir latest_execution();
- teste de regressão com execuções fora de ordem;
- garantir alinhamento entre analysis.version e ChecklistExecution.analysis_version ao criar o Veredito;
- preservar a pendência financeira existente;
- sem alteração de Verdict Engine, Risk Engine, RAG, LangGraph, agentes, Checklist Mestre, modelos ou migrations;
- sem nova análise real e sem V9;
- suíte backend completa.

**Commit esperado:** fix: corrige selecao da execucao do checklist

### Critério de aceite

Checklist V8 do imóvel 633 permanece em **7 CONFIRMADO / 20 PENDENTE** e o Veredito V8 deixa de tratar os 7 confirmados como pendentes. Pendências financeiras legítimas continuam separadas.

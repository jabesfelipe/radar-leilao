# RADAR LEILÃO — STATUS DO PROJETO

**Status global: MVP ENCERRADO — validação E2E real V9 concluída**

**Última atualização:** 28/09/2026  
**Última implementação aprovada:** Task 74.1 — commit 40c648d586ebb1a0beaef19ae7c4aa230fff7688

**Próximo passo:** nenhum. MVP encerrado; novas mudanças entram como Fase 2/backlog

## 1. Resumo executivo

O MVP do Radar Leilão está encerrado tecnicamente.

O fluxo principal foi implementado em Python/FastAPI + React/TypeScript, com PostgreSQL/pgvector, processamento documental com MarkItDown/OCR, RAG híbrido, LangChain/LangGraph, cinco agentes LLM especializados, Checklist Mestre, Risk Engine, Verdict Engine, histórico e memória estruturada.

A validação final utilizou o imóvel real COND PARQUE ARVOREDO RESIDENCIAL CLUBE, referência Caixa, e foi concluída com a Analysis V9 real, após a reconciliação controlada da V8.

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
| E2E real Caixa | OK | V9 executada com 5 agentes e LLM real |
| Testes backend | OK | 292 passed na Task 74.1 |
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

Últimos resultados registrados:

    Task 70 — pytest -q
    267 passed

    Frontend — Vitest
    90 passed

    TypeScript — tsc --noEmit
    OK

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


## 12. TASK 71 — APROVADA 🟢

Commit funcional: **8f9b54d** — `fix: corrige selecao da execucao do checklist`.

Auditoria concluída: `latest_execution()` passou a selecionar deterministicamente por `analysis_version DESC, id DESC`; `execution_for_version()` garante que `create_verdict()` use a execução correspondente à versão da Analysis. Foram adicionados 8 testes de regressão.

Validação reportada pelo Kiro: **275 passed**, 0 falhas; `origin/main == HEAD`. Nenhuma análise real, LLM, reanálise ou V9 foi executada.

Escopo preservado: VerdictEngine, RiskEngine, modelos, migrations, frontend, Checklist Mestre, RAG, LangGraph e agentes não foram alterados.

**Próximo passo:** rebuild/health e validação visual do imóvel 633. Somente após confirmar o Veredito V8 alinhado ao Checklist V8, seguir para V8 → DomainEvent → ImpactAnalyzer → reanálise incremental → V9.


## 13. TASK 72 — Diagnóstico da divergência Checklist × Veredito

**Status:** 🟡 especificada — diagnóstico somente, sem correção funcional ainda.

Validação manual do imóvel 633 após as Tasks 70/71 confirmou:

- Checklist V8: **7 CONFIRMADOS / 20 PENDENTES**;
- Evidências na UI agora estão legíveis e rastreáveis;
- Veredito exibido como **Analysis V8**;
- Veredito V8 continua registrando **28 pendências**;
- as 28 pendências correspondem às 27 perguntas do Checklist + 1 pendência financeira legítima;
- portanto, os 7 itens atualmente CONFIRMADOS do Checklist continuam aparecendo como pendentes no snapshot persistido do Veredito.

### Hipótese a ser confirmada

O VerdictEngine atual considera como pendência de Checklist somente estados PENDENTE e EM_ANALISE. A Task 71 também corrigiu a seleção determinística da ChecklistExecution correspondente à versão da Analysis.

Portanto, antes de alterar qualquer regra, é necessário determinar se:

1. o Veredito V8 foi criado quando a execução do Checklist ainda estava com os 27 itens PENDENTE e posteriormente os 7 foram atualizados para CONFIRMADO; ou
2. existe outra divergência entre a execução V8 persistida, a execução usada no create_verdict() e o snapshot pending_items do Veredito.

### Task 72 — escopo fechado

O Kiro deve **somente diagnosticar e testar**, sem corrigir ainda:

1. identificar todas as ChecklistExecution do imóvel 633 relevantes para V8;
2. registrar id, analysis_version, triggered_by e distribuição de estados;
3. identificar qual execução corresponde à V8 usada pelo create_verdict();
4. comparar essa execução com o Verdict V8 persistido;
5. determinar se pending_items é um snapshot histórico anterior às alterações do Checklist;
6. adicionar testes de diagnóstico/regressão somente se necessários para demonstrar a causa;
7. não alterar VerdictEngine;
8. não alterar Checklist Master ou regras de estados;
9. não alterar IncrementalAnalysisService, ImpactAnalyzer, RAG, LangGraph ou agentes;
10. não criar migration;
11. não executar LLM, nova análise ou V9;
12. não corrigir o comportamento ainda caso a causa seja apenas snapshot histórico;
13. executar a suíte completa.

### Critério de aceite

O resultado da Task 72 deve responder objetivamente:

> **Por que o Checklist V8 atual está 7 CONFIRMADO / 20 PENDENTE enquanto o Veredito V8 persistido contém 28 pendências?**

A resposta deve ser sustentada pelos registros/testes encontrados, sem suposição.

**Commit esperado:** `test: diagnostica divergencia checklist e veredito`

Se o diagnóstico demonstrar que o Veredito V8 é apenas um snapshot histórico anterior às confirmações do Checklist, **não corrigir nesta task**. Nesse caso, a próxima task será definida separadamente.

**Proibido:** gerar V9 ou executar reanálise real do imóvel 633.


---

## TASK 72 — DIAGNÓSTICO DA DIVERGÊNCIA CHECKLIST × VEREDITO — APROVADA 🟢

**Commit:** `0cb346335d95110eeb1bb8b8c82b8c88ea44f1dc`  
**Status:** 🟢 APROVADA — 28/09/2026  
**Testes:** `279 passed`, 0 falhas  
**Alteração funcional:** nenhuma; somente teste diagnóstico.

A causa raiz da divergência do imóvel 633 foi comprovada no banco real, sem alteração dos dados:

1. `Property.checklist_executions` não possui `order_by`; a ordem da coleção ORM em memória é incidental.
2. Na V8, a execução correta era a **1153**, com **7 CONFIRMADO / 20 PENDENTE**.
3. `create_execution()` cria a execução por `property_id`, sem anexá-la explicitamente à relationship `prop.checklist_executions`. Durante o request, a nova execução V8 não estava presente nessa coleção em memória.
4. O antigo `latest_execution()`, baseado em `reversed(prop.checklist_executions)`, selecionou a execução **665 (V3)**, que possuía **27 PENDENTE**.
5. O VerdictEngine recebeu essa execução antiga e corretamente produziu 27 pendências de Checklist + 1 pendência financeira = **28**.
6. As 7 confirmações da execução 1153 já existiam antes da criação do Veredito V8; portanto, não era simplesmente uma edição posterior do Checklist.
7. A Task 71 já corrigiu o caminho futuro com `execution_for_version(prop, analysis.version)`, evitando a seleção de outra versão.

Os quatro testes adicionados reproduzem o mecanismo de seleção incorreta, demonstram a seleção por versão da Task 71, demonstram o efeito no VerdictEngine e registram o comportamento da relationship quando a execução é criada por FK.

**Importante:** o Veredito V8 histórico não deve ser regravado. A Task 72 não alterou dados, regras de negócio, VerdictEngine, Checklist, modelos ou migrations.

### Próximo passo técnico

Antes de executar uma V9 real, deve ser tratada/validada a questão da **relationship `prop.checklist_executions` dentro do mesmo request**. A Task 71 seleciona a execução por versão dentro dessa coleção; portanto, é necessário garantir que uma execução recém-criada esteja disponível de forma determinística no fluxo de criação do Veredito.

**Próxima task proposta: Task 73 — Garantir acesso determinístico à ChecklistExecution recém-criada no mesmo request**, com escopo mínimo, testes de regressão e sem executar V9.


---

## TASK 73 — Garantir seleção da ChecklistExecution recém-criada — PRÓXIMA TASK

**Status:** 🟡 especificada — aguardando implementação/auditoria.

Após o diagnóstico da Task 72, existe uma fragilidade a ser fechada antes da primeira V9 real: `create_execution()` cria a `ChecklistExecution` por FK (`property_id=prop.id`) e a execução recém-criada pode não estar presente na coleção `prop.checklist_executions` já carregada na mesma sessão ORM.

A Task 71 corrigiu a regra de seleção por `analysis_version`, mas a Task 73 deve garantir que essa execução corrente seja efetivamente encontrada pelo fluxo de criação do Veredito.

### Objetivo

Garantir que, no mesmo request da análise/reanálise, o `create_verdict()` encontre deterministicamente a `ChecklistExecution` correspondente à `analysis.version`, independentemente da ordem incidental ou estado do cache da relationship ORM.

### Escopo fechado

- investigar `create_execution()`, `execution_for_version()` e `create_verdict()`;
- reproduzir o cenário de execução criada por FK e Veredito calculado no mesmo request;
- aplicar a menor correção segura;
- adicionar testes de regressão;
- manter a seleção por `analysis_version` como regra semântica;
- preservar o comportamento do Checklist e do VerdictEngine.

### Fora do escopo

- VerdictEngine;
- Risk Engine;
- Checklist Mestre;
- estados/regras do Checklist;
- RAG;
- LangGraph;
- agentes;
- IncrementalAnalysisService/ImpactAnalyzer, salvo leitura necessária para entender o fluxo;
- migrations;
- correção do Veredito V8 histórico;
- execução de LLM;
- nova análise real;
- geração de V9;
- refatoração geral.

### Critério de aceite

Em cenário equivalente ao fluxo real:

```
Analysis Vn
   ↓
create_execution()
   ↓
ChecklistExecution Vn criada
   ↓
atualizações do Checklist
   ↓
create_verdict()
   ↓
execution_for_version()
   ↓
encontra exatamente a ChecklistExecution Vn
```

A execução corrente deve ser encontrada deterministicamente mesmo que a relationship `prop.checklist_executions` tenha sido carregada antes da criação da nova execução.

### Validação

- testes novos cobrindo o cenário de mesma sessão/request;
- `pytest -q` completo;
- nenhum LLM;
- nenhum V9;
- dados do imóvel 633 preservados.

**Commit esperado:** `fix: garante selecao da execucao corrente do checklist`

Após aprovação da Task 73, o próximo marco será a validação operacional controlada **V8 → DomainEvent → ImpactAnalyzer → V9**.


---

## 14. VALIDAÇÃO REAL DO IMÓVEL 633 — 28/09/2026

### Estado atual

Após as Tasks 70 → 73.1, foi feita nova validação manual pela UI do imóvel **COND PARQUE ARVOREDO RESIDENCIAL CLUBE (property_id=633)**.

Confirmado na tela:

- Histórico preserva as análises V1–V8;
- Checklist V8: **7 CONFIRMADOS / 20 PENDENTES**;
- evidências do Veredito estão legíveis, com documento, categoria, versão e fonte quando disponíveis;
- Veredito exibido é **Analysis V8**.

### Divergência ainda existente

O Veredito V8 persistido continua apresentando **28 pendências**:

- 27 correspondem às perguntas do Checklist;
- 1 é uma pendência financeira legítima sobre a fórmula canônica de preço máximo.

Portanto, os 7 itens atualmente CONFIRMADOS no Checklist V8 ainda aparecem no snapshot histórico do Veredito como pendentes.

### Interpretação

As Tasks 71, 73 e 73.1 corrigiram a seleção determinística da execução do Checklist para o **fluxo de novas análises**:

`Analysis V8 → ChecklistExecution V8 → Risk Engine V8 → Verdict V8`

A divergência observada agora é do **Veredito V8 já persistido no banco**, criado antes das correções de seleção, e não deve ser corrigida gerando V9 ou executando novamente a análise completa.

### Regra de continuidade

**Não executar a análise completa do imóvel 633. Não gerar V9 ainda.**

A próxima task deve ser exclusivamente uma correção/reconciliação controlada do Veredito V8 histórico, sem LLM e sem alterar as regras do Checklist/Verdict Engine.

### Status

- Validação UI 633: 🟢 concluída;
- Checklist V8: 🟢 7/20;
- Evidências UI: 🟢 legíveis;
- Seleção corrente Checklist/Risk/Verdict para novas execuções: 🟢 corrigida nas Tasks 73/73.1;
- Veredito V8 histórico: 🔴 pendente de reconciliação;
- V9: ⏸️ bloqueada até a reconciliação e nova validação.


---

## 15. FECHAMENTO FINAL — 28/09/2026

### Tasks 73 → 74.1

- Task 73 — 🟢 aprovada: seleção da ChecklistExecution corrente por banco e `analysis_version`.
- Task 73.1 — 🟢 aprovada: Risk Engine alinhado à mesma execução semântica da Analysis.
- Task 74 — 🟢 concluída: reconciliação determinística do Veredito V8 histórico do imóvel 633.
- Task 74.1 — 🟢 aprovada: reconciliação estritamente limitada a `property_id=633` e `analysis_version=8`, sem criação de Verdict ausente.

### Reconciliação V8

O Verdict V8 histórico foi corrigido in place:

`28 pendências → 21 pendências`

Resultado validado na UI:

- Checklist V8: **7 CONFIRMADOS / 20 PENDENTES**;
- Veredito V8: **21 pendências**;
- histórico V1–V8 preservado;
- nenhum V9 criado pela manutenção.

### V9 real

Após a reconciliação, o imóvel 633 foi submetido à análise completa real pela UI.

Resultado:

- Analysis V9 criada;
- 5 agentes executados;
- LLM real ativo;
- 5/5 runs com sucesso;
- 8 chunks recuperados;
- 34.045 tokens;
- custo registrado: **US$ 0,00650625**;
- Checklist V9: **10 CONFIRMADOS / 17 PENDENTES**;
- Veredito V9: **INCONCLUSIVO**;
- 18 pendências totais: 17 do Checklist + 1 financeira;
- histórico V1–V9 preservado.

### Coerência documentação × implementação

Foi criada a referência:

`docs/IMPLEMENTATION-REFERENCE.md`

Ela mapeia os módulos efetivamente existentes do backend, pipeline documental/RAG, IA, domínio, frontend, migrations, scripts operacionais, testes, reconciliação histórica e critérios de encerramento.

A SPEC permanece como documento mestre de arquitetura/business. A nova referência documenta a implementação efetiva e suas limitações, evitando que arquitetura futura seja confundida com código já entregue.

### Estado final

**MVP FUNCIONALMENTE ENCERRADO.**

Não há Task 75 funcional planejada.

Qualquer nova capacidade — MCP externo, Knowledge Graph dedicado, integrações externas, comparáveis automatizados, fórmula de preço máximo, produção/hardening ou leilão judicial — deve ser tratada como **Fase 2 / backlog**.

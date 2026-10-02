# RADAR LEILÃO — STATUS DO PROJETO

**Status global: FECHAMENTO FUNCIONAL DO PRODUTO (TASK 75) — 12 menus navegáveis (sem placeholder), hubs globais, domínio Leiloeiros, break-even e nova identidade visual; testes automatizados verdes; E2E de NAVEGADOR (Playwright) ainda pendente por falta de ambiente; MVP ainda NÃO encerrado**

**Última atualização:** 01/10/2026  
**Última implementação:** TASK 75 — fechamento funcional: hubs globais (Dashboard/Documentos/Jurídico/Financeiro/Mercado/Ocupação/Checklist/Riscos/Veredito/Histórico), domínio Leiloeiros com credenciais protegidas (migration `0014`), break-even no Finance Engine e nova identidade visual. Detalhes na §23.

**Próximo passo (impeditivo do encerramento):** executar o E2E financeiro pela INTERFACE em um navegador real e registrar as evidências. Não há automação de navegador (Playwright/Cypress) no projeto, então essa validação permanece manual. Até ela ser concluída e registrada, o MVP NÃO é declarado encerrado.

> **Nota de leitura:** as seções históricas abaixo preservam o registro das etapas anteriores (o "encerramento" de 28/09 permanece como histórico e NÃO reflete o estado atual). O estado atual e autoritativo está no cabeçalho e nas seções das Tasks 4 e 5 (última implementação registrada); as seções anteriores preservam o histórico. Consulte também `docs/IMPLEMENTATION-REFERENCE.md`.

## 1. Resumo executivo

**Registro histórico anterior:** os parágrafos e tabelas abaixo descrevem capacidades implementadas em etapas anteriores; não significam que o fechamento atual tenha sido aprovado. O estado atual exige a validação E2E financeira manual pela UI; os testes HTTP da Task 5 não a substituem.

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


---

## 16. AUDITORIA — VALIDAÇÃO FINAL REABERTA — 30/09/2026

> **Nota histórica:** a tabela e o backlog desta auditoria registram o estado observado antes das correções financeiras das Tasks 2–5. Para o estado atual, prevalecem a reconciliação da §16.4 e os registros das Tasks 17–20. Itens marcados como históricos abaixo não são pendências atuais quando já endereçados nas Tasks posteriores.

**Data da revisão:** 30/09/2026
**Estado:** validação final reaberta para confirmar funcionamento real. O encerramento
anterior (seções 8 e 15) permanece preservado no histórico — nada foi apagado ou
reescrito. Esta seção registra o resultado da auditoria baseada em evidências.

> Regra desta auditoria: **não implementar funcionalidades de produto**; apenas
> registrar o estado real. Nenhum código de aplicação, contrato de API, banco,
> migração ou teste foi alterado nesta task.

### 16.1 Evidência de execução dos testes

- Comando: `python -m pytest -q` no container `radar-leilao-backend`.
- Ambiente: PostgreSQL real (`RAG_TEST_DATABASE_URL` apontando para `radar_leilao`),
  **sem LLM e sem rede** (`OPENAI_API_KEY` vazio, `OCR_ENABLED=false`), `PYTHONPATH=/app`.
- Resultado real: **476 passed, 2 skipped, 0 falhas** (exit 0). Os 2 skips são os testes
  reais do DataJud, propositalmente condicionados a `RUN_REAL_DATAJUD_TESTS=true`.
- Migration head aplicada: `0011_judicial_persistence` (cadeia Alembic única).
- Git: branch `main`, HEAD `62fe23d`; árvore de trabalho sem alterações de conteúdo
  pendentes (apenas avisos cosméticos de fim de linha CRLF→LF).

### 16.2 Legenda de status (rastreabilidade honesta)

- **Comprovado (teste executado):** coberto por teste automatizado que rodou com sucesso nesta auditoria.
- **Implementado (código):** existe no código, mas não validado manualmente em cenário real nesta task.
- **Parcial:** existe, porém incompleto ou com placeholder declarado.
- **Fora do MVP:** decisão explícita de escopo.
- **Não verificado:** não foi possível validar nesta auditoria (ex.: exige credencial/rede externa).

### 16.3 Tabela de auditoria

| Área | Status | Evidência | Impacto | Correção mínima | Prioridade | Critério de aceite |
|---|---|---|---|---|---|---|
| Financeiro — custos/comissão/desconto/margem/yield | Comprovado (teste) | `backend/app/finance.py::calculate_financial`; `tests/test_finance.py` (custo total, comissão %/fixa, desconto, margem, yield, divisão por zero) | Base financeira determinística confiável | — | — | Testes de finance passam (ok) |
| Financeiro — preço máximo de lance | Parcial (placeholder declarado) | `finance.py::calculate_max_acquisition_price` retorna `None`; `result["pendencias"]` declara ausência de fórmula canônica; `tests/test_finance.py::test_cenarios_sao_estruturas_neutras_e_preco_maximo_pendente` | Sem preço máximo, a decisão de lance fica sem teto objetivo | Definir fórmula canônica na SPEC e então implementar | P1 | SPEC define fórmula; `calculate_max_acquisition_price` a implementa; teste cobre valores esperados |
| Financeiro — cenários conservador/base/otimista | Parcial | `finance.py`: lista `scenarios` repete os mesmos valores para BASE/OTIMISTA/PESSIMISTA (estrutura neutra) | Cenários não diferenciam risco; UI pode sugerir modelagem inexistente | Modelar premissas por cenário (ou rotular explicitamente como neutro na UI) | P1 | Cada cenário reflete premissas distintas com teste; ou UI deixa claro que é neutro |
| Financeiro — tributação na venda, corretagem, lucro líquido, ROI temporal, margem de segurança | Ausente (fora do cálculo atual) | `finance.py` não calcula esses itens; `roi_estimado_percentual` é alias de `margem_percentual` (não ROI temporal) | Retorno pós-venda e carga tributária não entram na decisão | Especificar e implementar cálculo de venda (impostos + corretagem + prazo) | P1 | Fórmulas na SPEC + implementação + testes de lucro líquido/ROI |
| Mercado — consolidação de comparáveis | Comprovado (teste) | `backend/app/market.py::calculate_market` (média/mediana, preço/m², aluguel); `tests/test_market.py` | Agrega apenas o que foi cadastrado; sem invenção de dados | — | — | Testes de market passam (ok) |
| Mercado — origem/data/confiabilidade, ajustes, valor conservador, liquidez, prazo | Ausente (por design atual) | `market.py` docstring "sem scoring ou valuation"; comparáveis vêm de cadastro manual (`POST /api/imoveis/{id}/comparaveis`) | Sem ajuste/liquidez, o valor de venda é apenas média de comparáveis informados | Especificar ajustes e estimativa conservadora/liquidez | P2 | SPEC define método; implementação + testes; sem dado simulado como fato |
| Jurídico — cadastro manual de processos (E2E) | Comprovado (teste) | `POST/GET /api/imoveis/{id}/processos` em `main.py`; `tests/test_processes.py` (campos, opcionais, 404, histórico) | Entrada manual de processos funciona ponta a ponta | — | — | Testes de processes passam (ok) |
| Jurídico — integração DataJud por número de processo + persistência PG | Comprovado (teste, com mock) | `judicial_client.py`, `judicial_integration.py`, `POST /api/imoveis/{id}/processos/consultar`; `tests/test_judicial_client.py`, `tests/test_judicial_integration_pg.py`, `tests/judicial/test_postgres_store.py` | Consulta e persistência funcionam; falha da Judicial API não bloqueia análise | — | — | Testes passam (ok); validação real permanece opcional |
| Jurídico — consulta real ao DataJud (rede) | Não verificado | Transporte real `HttpxTransport` implementado e injetado; teste real gated (`tests/judicial/test_real_datajud.py`, skip sem `RUN_REAL_DATAJUD_TESTS`) | Sem credencial/conectividade, a consulta real não foi exercitada nesta auditoria | Rodar teste real com credencial pública + conectividade | P2 | Teste real executa e retorna dados/vazio sem erro |
| Jurídico — descoberta por nome/CPF/CNPJ na API pública | Fora do MVP | `judicial_api/providers/datajud.py` ergue `UNSUPPORTED_SEARCH_CRITERIA`; capabilities `name/cpf/cnpj=false` | A API pública DataJud não oferece essa descoberta | Não desenvolver enquanto não houver fonte adequada e autorizada | P2 | N/A enquanto fora do MVP |
| Documentos e Checklist | Comprovado (teste) | Pipeline em `backend/app/documents/`; `checklist.py` (27 itens, estados); evidências + trilha (`DomainEvent`/`EntityHistory`); `tests/test_documents.py`, `test_extraction.py`, `test_checklist*.py`, `test_evidence*.py` | Base documental/checklist/auditoria confiável | — | — | Testes passam (ok) |
| Veredito — consolidação e bloqueio por risco crítico | Comprovado (teste) | `verdict_engine.py` (CRITICA→DESFAVORAVEL; sem evidência→INCONCLUSIVO); `risk_engine.py` (risco só com evidência); `tests/test_verdict_engine.py`, `test_risk_engine.py` | Ausência de dados não vira positivo; risco crítico bloqueia | — | — | Testes passam (ok) |
| Fluxo E2E (cadastro→documentos→análise→checklist→jurídico→veredito→histórico) | Comprovado (teste) + Validado manual (V9, sessão anterior) | Endpoints em `main.py`; `tests/test_integration_flows.py`; histórico V1–V9 (seção 15) | Fluxo essencial funciona | — | — | Testes de integração passam (ok) |
| Entrega — testes/migrations/PostgreSQL/Docker | Comprovado (teste) | `pytest -q` = 476 passed / 2 skipped; migration head `0011`; `docker-compose.yml` (postgres, backend, judicial_api, frontend) | Ambiente reproduzível localmente | — | — | Suíte verde no container (ok) |

### 16.4 Backlog priorizado de correções (com critério de aceite)

> **Reconciliação (Tasks 2–5):** esta lista é o registro histórico da auditoria de
> 30/09/2026. Os P1 financeiros abaixo foram posteriormente endereçados: a **fórmula
> canônica de preço máximo** e o **financeiro de venda** (tributação, corretagem,
> lucro líquido, ROI da operação, margem) foram definidos na SPEC (ADDENDUM Task 2) e
> implementados em `finance.py` (Tasks 2–4); os **cenários** passaram a usar premissas
> explícitas (Task 2); as **premissas** passaram a ser coletadas por endpoint/UI e
> persistidas (Task 3, migration `0012`); o **preço máximo definitivo × provisório**
> foi tratado na Task 4; e o **E2E financeiro** foi validado por testes HTTP na Task 5
> (§20). Permanece aberto apenas o **P1 de validação E2E visual pela UI (navegador)**.
> Ver §17, §18, §19 e §20. Os itens P2 (mercado, DataJud real) seguem como Fase 2.

**P0 — impedem decisão segura / corrompem dados:** nenhum P0 identificado nesta auditoria.

**P1 — registro histórico da auditoria (não representa o status atual):**
1. **Preço máximo de lance** — registrado como placeholder na auditoria original; endereçado nas Tasks 2–4.
2. **Cenários financeiros** — registrados como neutros na auditoria original; tratados com premissas explícitas nas Tasks 2–3.
3. **Financeiro de venda** (tributação, corretagem, lucro líquido, ROI e margem) — registrado como ausente na auditoria original; implementado nas Tasks 2–4.

**P2 — melhorias não bloqueantes / futuras:**
4. **Mercado**: ajustes por área/localização/conservação, valor de venda conservador, liquidez e prazo de venda. Aceite: método na SPEC + implementação + testes; nenhum dado simulado apresentado como fato.
5. **Consulta real ao DataJud**: executar o teste real gated com credencial pública e conectividade. Aceite: `RUN_REAL_DATAJUD_TESTS=true` retorna processos/vazio sem erro.
6. **Descoberta de processos por nome/CPF/CNPJ**: fora do MVP enquanto não houver fonte adequada e autorizada.

### 16.5 O que fica explicitamente fora do MVP

- Descoberta automática de processos por **nome/CPF/CNPJ** (a API pública do DataJud não suporta; nunca simular capacidade).
- Valuation de mercado com ajustes e liquidez automatizada (Fase 2).
- Consulta real ao DataJud ainda não validada por execução com rede; manter como pendência P2 até haver evidência.

### 16.6 Plano mínimo para a Task 2 (registro histórico)

O plano abaixo documenta a sequência originalmente proposta e foi executado pelas Tasks 2–5; não é uma lista de tarefas ainda abertas:

1. Definir na SPEC a fórmula canônica de preço máximo e o financeiro de venda — endereçado nas Tasks 2–4.
2. Implementar cálculos determinísticos e tratamento de dados ausentes — endereçado nas Tasks 2–4.
3. Tratar cenários financeiros com premissas explícitas — endereçado nas Tasks 2–3.
4. Avançar em mercado e consulta real ao DataJud — permanecem como evolução/validação P2, conforme §16.5.

### 16.7 Critérios objetivos para declarar o MVP concluído

- Suíte completa verde no container (mantida): `pytest -q` sem falhas.
- Preço máximo e financeiro de venda definidos na SPEC e implementados com testes (P1 resolvidos).
- Cenários financeiros diferenciados ou explicitamente rotulados na UI.
- Fluxo E2E real revalidado (imóvel real) após os P1, com Veredito coerente (risco crítico bloqueia; ausência de dados não vira positivo).
- Documentação (STATUS/HISTORY/SPEC/backlog) coerente com o código, sem fonte concorrente.

### 16.8 Documentos atualizados nesta auditoria

- `docs/PROJECT-STATUS.md` — esta seção 16 (nova; histórico preservado).

Nenhum outro documento, código ou teste foi alterado.


---

## 17. TASK 2 — CORREÇÕES FINANCEIRAS P0/P1 IMPLEMENTADAS — 30/09/2026

**Data:** 30/09/2026
**Escopo:** correções confirmadas na auditoria (seção 16), sem funcionalidades fora
de escopo. Histórico preservado.

### 17.1 O que foi corrigido (com evidência)

- **Fórmulas canônicas na SPEC** (`docs/SPEC-VIBE-CODING-RADAR-LEILAO.md`, ADDENDUM
  Task 2): custo total de aquisição/operação/carregamento; resultado líquido de
  venda (corretagem + tributos parametrizáveis, sem dupla contagem); margem
  líquida; ROI da operação; preço máximo por meta configurável (LUCRO_MINIMO /
  MARGEM_MINIMA / ROI_MINIMO), com exemplos numéricos verificáveis e dependências
  explícitas. Nenhuma alíquota legal/custo fixo universal embutido.
- **`backend/app/finance.py`**:
  - `calculate_max_acquisition_price(...)` deixou de retornar `None` fixo: resolve o
    maior lance compatível com a meta, tratando comissão %/fixa, custos fixos e
    custos de saída, com resolução consistente do tributo base GANHO (sem dupla
    contagem). **Falha-segura**: sem valor de venda ou sem meta, retorna
    `preco_maximo=None` + pendência; cenário inviável retorna `viavel=false`. Nunca
    substitui premissa ausente por zero.
  - Resultado da operação: `resultado_liquido`, `margem_liquida`, `roi_operacao`
    (distintos da margem bruta), `custo_saida` (corretagem + tributos). Custo de
    carregamento incluído no breakdown.
  - Pendências reais sinalizadas (valor de venda ausente, corretagem/tributo não
    informados, ITBI/registro ausentes, meta de preço máximo não configurada) —
    fluem para o Veredito via `financial["pendencias"]`.
- **Cenários** base/otimista/pessimista: usam a MESMA fórmula, variando premissas
  explícitas e configuráveis (`ScenarioAssumptions`). Sem premissas informadas,
  otimista/pessimista são marcados como **pendentes** (não se inventam números).
- **`backend/app/market.py`**: adicionada sinalização de qualidade da amostra
  (suficiência vs. mínimo recomendado de 7, dispersão via coeficiente de variação,
  `avaliacao_definitiva=false`) e preservação de origem/URL/data das fontes. A
  média/mediana deixa de ser apresentada como avaliação definitiva.
- **Veredito/parecer**: sem alterar o `VerdictEngine` (aprovado), o veredito agora
  reflete as pendências financeiras reais — um resultado FAVORAVEL não sai com
  custos essenciais desconhecidos tratados como zero.

### 17.2 Jurídico manual (confirmado, sem alteração de código)

O cadastro manual de processos existe ponta a ponta: `POST /api/imoveis/{id}/processos`
e `GET /api/imoveis/{id}/processos` (`backend/app/main.py`), com estados, associação
ao imóvel, histórico e sem duplicação óbvia (`tests/test_processes.py`). A descoberta
por nome/CPF/CNPJ **permanece fora do escopo** (a API pública do DataJud não suporta;
`UNSUPPORTED_SEARCH_CRITERIA`). Nada foi implementado nesse sentido.

### 17.3 Testes executados (evidência real)

- Comando: `python -m pytest -q` no container `radar-leilao-backend`, PostgreSQL
  real (`RAG_TEST_DATABASE_URL`), **sem LLM/rede** (`OPENAI_API_KEY` vazio,
  `OCR_ENABLED=false`).
- `tests/test_finance.py`: **21 passed** (preço máximo por lucro/margem/ROI com % e
  fixos, verificação do resultado, inviável, pendências, resultado líquido,
  corretagem/tributos, cenários com premissas).
- Suíte completa: **494 passed, 2 skipped, 0 falhas**. Os 2 skips são os testes
  reais do DataJud (gated por `RUN_REAL_DATAJUD_TESTS`). Os 2 testes de veredito que
  dependiam da contagem de pendências foram atualizados para a nova regra (contam
  pendências de checklist e financeiras separadamente) — não foram afrouxados; ao
  contrário, o veredito ficou mais rigoroso.

### 17.4 Pendências remanescentes (por prioridade)

- **P1 — parametrização de entrada na UI/endpoint**: as premissas de venda (metas,
  corretagem, tributo) e de cenários hoje são aceitas pela camada de cálculo, mas o
  endpoint financeiro (`build_finance`) ainda não coleta essas premissas de um
  cadastro do usuário — por isso o preço máximo aparece como pendência no fluxo
  padrão até que as premissas sejam informadas. Critério de aceite: cadastro/endpoint
  para metas e premissas de venda/cenário, com testes.
- **P2 — mercado**: ajustes por localização/conservação e estimativa de valor
  conservador/liquidez continuam fora do escopo (sinalização de qualidade já
  implementada).
- **P2 — consulta real ao DataJud**: teste real permanece gated; não validado sem
  credencial/conectividade.

### 17.5 Validação manual ainda necessária

- Reexecução E2E real de um imóvel após informar metas/premissas financeiras, para
  confirmar o preço máximo e o resultado líquido no fluxo completo pela UI.

### 17.6 Status do MVP

O MVP **não** é declarado concluído nesta task: permanece a pendência P1 de coleta
das premissas financeiras na camada de entrada (endpoint/UI) para que o preço máximo
saia do estado "pendente" no fluxo padrão. As fórmulas e o motor determinístico estão
implementados e cobertos por testes.

### 17.7 Arquivos alterados nesta task

- `docs/SPEC-VIBE-CODING-RADAR-LEILAO.md` — ADDENDUM Task 2 (fórmulas/exemplos).
- `backend/app/finance.py` — preço máximo, resultado líquido, cenários, pendências.
- `backend/app/market.py` — qualidade da amostra e rastreabilidade de fontes.
- `tests/test_finance.py`, `tests/test_market.py` — novas expectativas corretas.
- `tests/test_reconcile_verdict.py`, `tests/test_execution_same_session_selection.py`
  — contagem de pendências atualizada para a nova regra (checklist vs. financeiras).
- `docs/PROJECT-STATUS.md` — esta seção 17.

Nenhum contrato de API, migração ou modelo foi alterado. Nenhuma credencial versionada.


---

## 18. TASK 3 — INTEGRAÇÃO DAS PREMISSAS FINANCEIRAS E FECHAMENTO P0/P1 — 30/09/2026

**Escopo:** fechar a pendência P1 da Task 2 (premissas financeiras não chegavam ao
motor pela camada de entrada) e os pontos P0/P1 de confiabilidade financeira.
Histórico preservado.

### 18.1 O que foi implementado

- **Persistência das premissas** (migration `0012_premissas_financeiras`): coluna
  JSON `auctions.financial_assumptions` (reversível, nullable, sem tocar em dados).
  Guarda meta de preço máximo, corretagem, tributo (+ base), valor de venda
  estimado, prazo e carregamento mensal.
- **`build_finance`** (`services.py`) agora lê essas premissas e constrói
  `SaleAssumptions` / `MaxPriceGoal` / `ScenarioAssumptions`, repassando ao motor.
  O **preço máximo passa a ser calculado no fluxo normal** (dossiê e `/financeiro`),
  com `preco_maximo_detalhe` (componentes/pendências).
- **Endpoints** (`main.py`): `PUT/GET /api/imoveis/{id}/financeiro/premissas`
  (informar/recuperar, com validação Pydantic de negativos/limites/combinações);
  `analyze_financial` snapshota as premissas em `FinancialAnalysis.inputs`
  (histórico preservado por versão).
- **P0 — custo desconhecido ≠ zero** (`finance.py`): cada custo é classificado
  (INFORMADO/ESTIMADO/DESCONHECIDO/NAO_APLICAVEL); custos materiais de aquisição
  (ITBI/registro) e de saída (corretagem/tributo) não informados ficam
  DESCONHECIDO. O resultado líquido calculável, porém com custos materiais
  desconhecidos, é marcado `resultado_provisorio=true`/`resultado_completo=false` —
  não é apresentado como conclusivo.
- **Prazo × carregamento** (`finance.py`): premissa `carregamento_mensal` é
  multiplicada por `holding_months` (`carregamento_recorrente`), somada ao custo de
  carregamento único sem dupla contagem; reflete em custo total, resultado e ROI.
- **Cenários**: base/otimista/pessimista com a mesma fórmula e premissas explícitas;
  sem premissas, otimista/pessimista permanecem pendentes (nada inventado).
- **Mercado**: qualidade da amostra e fontes agora chegam ao dossiê/endpoint e são
  exibidas na interface (quantidade, médias/medianas, m², amostra insuficiente,
  dispersão elevada; "não é avaliação definitiva").
- **Veredito**: sem alterar o `VerdictEngine`, as pendências financeiras reais
  fluem para o parecer; com premissas completas, elas desaparecem. Um resultado não
  fica FAVORAVEL com custos essenciais desconhecidos.
- **Frontend**: `FinancialSection` informa premissas e exibe custo total, custo de
  saída, resultado líquido, margem líquida, ROI, preço máximo, pendências e o aviso
  de resultado provisório; `MarketSection` exibe a qualidade da amostra.

### 18.2 Testes executados (evidência real)

- Backend: `python -m pytest -q` no container `radar-leilao-backend`, PostgreSQL
  real (`RAG_TEST_DATABASE_URL`), **sem LLM/rede** → **506 passed, 2 skipped, 0
  falhas**. Migration `0012` aplicada (`0011 → 0012`). Os 2 skips são os testes
  reais do DataJud (gated). `tests/test_finance.py` = 30 passed (inclui resultado
  provisório, carregamento×prazo, preço máximo por lucro/margem/ROI, inviável);
  `tests/test_finance_assumptions.py` cobre build_finance, endpoints, persistência,
  reexecução e preservação de histórico.
- Frontend: `npx tsc --noEmit` OK; `npx vitest run` → **93 passed (16 arquivos)**.
  Novos testes de `FinancialSection` (premissas/resultado) e `MarketSection`
  (qualidade); testes de mock ajustados por URL (não afrouxados).

### 18.3 Validação E2E manual — PENDENTE

A validação ponta a ponta pela interface (cadastrar imóvel → informar premissas →
executar análise → conferir preço máximo/resultado/cenários/veredito → reabrir e
confirmar persistência → alterar premissa e reexecutar preservando histórico)
**não foi executada nesta task** (exige interação manual na UI e LLM real). Fica
registrada como pendência de validação; não é simulada como aprovada.

### 18.4 Pendências remanescentes (por prioridade)

- **P1**: validação E2E manual do fluxo financeiro pela UI (acima).
- **P2**: mercado — ajustes por localização/conservação e estimativa conservadora/
  liquidez (sinalização de qualidade já entregue).
- **P2**: consulta real ao DataJud (teste gated, não validado sem credencial/rede).

### 18.5 Critérios de aceite da Task 3

1. API/UI informam e recuperam premissas — **atendido** (endpoints + FinancialSection).
2. Preço máximo no fluxo normal quando há dados — **atendido** (build_finance repassa goal).
3. Custos desconhecidos sinalizados; parcial não é conclusivo — **atendido** (resultado_provisorio).
4. Prazo reflete carregamento — **atendido** (carregamento mensal × prazo).
5. Cenários/cálculo/veredito consistentes — **atendido** (mesma fórmula; pendências no veredito).
6. Premissas persistidas e histórico preservado — **atendido** (Auction + snapshot em inputs).
7. Testes executados com resultados registrados — **atendido** (506 backend / 93 frontend).
8. Documentação corresponde ao estado real — **atendido** (esta seção + status global).
9. E2E executado OU limitação registrada — **limitação registrada** (18.3).
10. Sem falhas P0/P1 ocultadas — a única P1 aberta (E2E manual) está declarada.

### 18.6 Arquivos alterados

- `backend/app/finance.py`, `backend/app/services.py`, `backend/app/main.py`,
  `backend/app/models.py`, `backend/app/schemas.py`,
  `backend/migrations/versions/0012_premissas_financeiras.py`,
  `frontend/src/services/finance.ts`, `frontend/src/services/market.ts`,
  `frontend/src/pages/FinancialSection.tsx`, `frontend/src/pages/MarketSection.tsx`,
  `tests/test_finance.py`, `tests/test_finance_assumptions.py`,
  `frontend/src/pages/FinancialSection.test.tsx`,
  `frontend/src/pages/MarketSection.test.tsx`,
  `frontend/src/pages/PropertyDetailPage.test.tsx`,
  `docs/SPEC-VIBE-CODING-RADAR-LEILAO.md` (regra do carregamento mensal),
  `docs/PROJECT-STATUS.md` (esta seção + status global).

Nenhuma credencial versionada. Nenhuma busca jurídica por nome/CPF/CNPJ. Sem novos
fornecedores, infraestrutura cloud ou refatorações amplas.


---

## 19. TASK 4 — PREÇO MÁXIMO SEGURO (definitivo × provisório) — 30/09/2026

**Escopo:** corrigir o preço máximo que podia parecer definitivo quando havia
custos materiais desconhecidos. Histórico preservado.

### 19.1 O que foi corrigido

- `calculate_max_acquisition_price` (`backend/app/finance.py`) recebe
  `unknown_costs` e passa a devolver `definitivo`/`provisorio`. Com dados essenciais
  presentes mas custos materiais desconhecidos, o preço é uma **estimativa
  provisória** (`definitivo=false`), com aviso listando as premissas faltantes — os
  custos desconhecidos entram como zero apenas na simulação parcial, nunca sem
  aviso, e o valor NÃO é apresentado como limite confiável.
- `calculate_financial` monta a lista de custos materiais desconhecidos (ITBI,
  registro, **comissão de arrematação** quando não informada, corretagem e tributo
  de venda) e a repassa; expõe `preco_maximo_definitivo`/`preco_maximo_provisorio`.
- Não se inventam percentuais/impostos/custos padrão para "fechar a conta".
- Frontend (`FinancialSection`): distingue "Preço máximo definitivo" de
  "Preço máximo (estimativa provisória)", com aviso e lista de custos desconhecidos.

### 19.2 Testes executados (evidência real)

- Backend (`python -m pytest -q`, container, PostgreSQL real, sem LLM/rede):
  **514 passed, 2 skipped, 0 falhas**. `tests/test_finance.py` = **33 passed**
  (cobre: todos informados → definitivo; ITBI/registro, comissão, corretagem,
  tributo desconhecidos → provisório; metas lucro/margem/ROI; inviável; premissas
  completas → preço máximo esperado 234000/1,05).
- Frontend: `npx tsc --noEmit` OK; `npx vitest run` → **95 passed (16 arquivos)**
  (novos testes de preço máximo provisório e definitivo em `FinancialSection`).

### 19.3 Exemplos numéricos validados

- Definitivo: V=320k, comissão 5%, ITBI 10k, registro 20k (F=30k), corretagem 5%,
  tributo 0, meta lucro 40k → **preço máximo = 234000/1,05 = 222.857,14**,
  `definitivo=true`.
- Provisório: mesmos dados sem ITBI/registro informados → valor calculado, porém
  `provisorio=true` e `custos_desconhecidos` inclui `itbi`/`registro` (o teto real
  seria menor ao incluí-los).

### 19.4 Validação E2E manual — PENDENTE

A validação ponta a ponta pela interface (premissas → salvar/recarregar → conferir
preço máximo/resultado/cenários → deixar premissa material desconhecida e confirmar
o aviso → alterar premissa e reexecutar preservando histórico) **não foi executada**
(exige interação manual na UI e LLM real). Registrada como pendência P1; não simulada.

### 19.5 Pendências remanescentes

- **P1**: validação E2E manual do fluxo financeiro pela UI.
- **P2**: mercado (ajustes por localização/conservação, valor conservador/liquidez);
  consulta real ao DataJud (teste gated).

### 19.6 Arquivos alterados

- `backend/app/finance.py`, `tests/test_finance.py`,
  `frontend/src/services/finance.ts`, `frontend/src/pages/FinancialSection.tsx`,
  `frontend/src/pages/FinancialSection.test.tsx`,
  `docs/SPEC-VIBE-CODING-RADAR-LEILAO.md`, `docs/PROJECT-STATUS.md`.

Sem novas integrações, fornecedores, infraestrutura ou refatorações amplas. Nenhuma
credencial versionada. MVP **não** declarado encerrado (E2E manual pendente).


---

## 20. TASK 5 — VALIDAÇÃO E2E DO FLUXO FINANCEIRO — 30/09/2026

**Escopo:** validar e automatizar (no viável) o fluxo financeiro de ponta a ponta,
das premissas à persistência e apresentação. Histórico preservado.

### 20.1 Diagnóstico

- Não há infraestrutura de E2E de navegador no projeto: o frontend usa apenas
  `vitest` + `@testing-library` (jsdom); **Playwright/Cypress NÃO estão instalados**
  (`frontend/package.json`).
- A cobertura financeira até a Task 4 exercitava o motor (`test_finance.py`) e os
  endpoints chamados como funções Python (`test_finance_assumptions.py`), mas **não**
  havia um teste que exercitasse o fluxo pela camada HTTP real (request → rota →
  PostgreSQL → resposta JSON).
- Decisão de escopo mínimo: adicionar um **E2E de integração HTTP** com o
  `TestClient` do FastAPI (menor dependência adicional — reutiliza `httpx` já
  presente e o padrão de override de `get_db` com savepoint de
  `tests/test_integration_flows.py`, isolado por transação, sem tocar dados reais).
  O E2E de **navegador** permanece como validação manual (não há ambiente para
  browser automation aqui) — não foi simulado.

### 20.2 O que foi adicionado

- `tests/test_e2e_financeiro.py` — 12 testes HTTP cobrindo os 10 cenários da Task 5.

### 20.3 Cenários cobertos (via HTTP real)

1. Premissas materiais completas → preço máximo DEFINITIVO. ✓
2. ITBI desconhecido → provisório + `custos_desconhecidos` inclui `itbi`. ✓
3. Registro desconhecido → provisório. ✓
4. Comissão de arrematação desconhecida → provisório. ✓
5. Corretagem de venda desconhecida → provisório. ✓
6. Tributo de venda desconhecido → provisório. ✓
7. Salvar premissas, recarregar (GET) e confirmar persistência. ✓
8. Nova análise não altera o snapshot da anterior (histórico por versão). ✓
9. Metas lucro/margem/ROI + cenário inviável (`META_INATINGIVEL`). ✓
10. Erros de validação (422: percentual fora de 0–1; meta incompleta) e 404. ✓

### 20.4 Testes executados (evidência real)

- `python -m pytest -q tests/test_e2e_financeiro.py` (container, PostgreSQL real,
  sem LLM/rede) → **12 passed**.
- Suíte backend completa → **526 passed, 2 skipped, 0 falhas** (os 2 skips são os
  testes reais do DataJud, gated). Zero regressão.
- Frontend: inalterado nesta task (última execução Task 4: tsc OK + vitest 95 passed).

### 20.5 Cenários NÃO executados / limitações

- **E2E de navegador (UI real)**: não executado — sem Playwright/Cypress instalados
  e sem ambiente de browser automation. Continua como validação MANUAL (passos em
  20.6). O E2E HTTP cobre o backend de ponta a ponta, mas não a renderização/estados
  do React no navegador.
- Testes reais do DataJud: gated, não executados.

### 20.6 Passos para validação manual (UI)

1. Subir o ambiente (`docker compose up -d`) e abrir o frontend.
2. Cadastrar um imóvel de teste e informar o leilão.
3. Na aba Financeiro, informar as premissas (meta, valor de venda, corretagem,
   tributo, prazo, carregamento mensal) e salvar.
4. Recarregar a página e confirmar que as premissas persistem.
5. Deixar ITBI/registro/comissão/corretagem/tributo em falta e confirmar o aviso
   "Preço máximo (estimativa provisória)" com a lista de custos desconhecidos.
6. Preencher todas as premissas materiais e confirmar "Preço máximo definitivo".
7. Alterar uma premissa, reexecutar a análise e confirmar no histórico que a versão
   anterior permanece inalterada.

### 20.7 Arquivos alterados

- `tests/test_e2e_financeiro.py` (novo).
- `docs/PROJECT-STATUS.md`, `docs/IMPLEMENTATION-REFERENCE.md`,
  `docs/PROJECT-HISTORY.md` (registro).

Nenhuma migration, regra de negócio, contrato ou infraestrutura foi alterado. Nenhum
dado real de imóvel foi tocado (isolamento por transação/rollback). O MVP **não** é
declarado encerrado enquanto a validação E2E manual da UI não for executada.


---

## 21. VALIDAÇÃO DE FECHAMENTO DO MVP — 30/09/2026

Rodada de validação para decidir o fechamento do MVP após as Tasks 2–5 e a
correção `788d749`. Nenhuma regra de negócio foi alterada; o histórico anterior é
preservado. O estado abaixo é o autoritativo.

### 21.1 Ambiente e sincronização
- Branch `main`, HEAD `788d749` (fix da seleção determinística do leilão corrente),
  sincronizado com `origin/main` (`git pull --ff-only` = *Already up to date*).
- Containers Docker saudáveis: `backend` (8000), `frontend` (5173), `judicial_api`
  (8010), `postgres` (5432); `/health` dos três serviços = 200. O backend em
  execução contém o código atual (imagem rebuildada com `788d749`).
- Migration head aplicada no banco: `0012_premissas_financeiras`.

### 21.2 Testes automatizados (evidência real desta rodada)
- Backend (container, PostgreSQL real, sem LLM/rede): **527 passed, 2 skipped, 0
  falhas**. Os 2 skips são os testes reais do DataJud (gated por
  `RUN_REAL_DATAJUD_TESTS`). O total subiu de 526 → 527 pelo teste de regressão
  multi-leilão adicionado com a correção `788d749`.
- Financeiro (`test_finance.py`, `test_finance_assumptions.py`,
  `test_e2e_financeiro.py`): **54 passed**, incluindo o cenário de múltiplos leilões.
- Frontend: `tsc --noEmit` sem erros; `vitest run` = **90 passed (16 arquivos)**.
  (Registros anteriores citavam 95; o número real atual é 90.)

### 21.3 E2E financeiro de NAVEGADOR — NÃO EXECUTÁVEL (pendência impeditiva)
- O projeto não possui automação de navegador: `frontend/package.json` traz apenas
  `vitest` + `@testing-library` sobre `jsdom`; **não há Playwright/Cypress/Puppeteer/
  Selenium/WebdriverIO** nem script e2e. Testes jsdom/HTTP não contam como E2E de
  navegador.
- Portanto, o fluxo financeiro **no navegador** não foi validado nesta rodada.
  Permanece como **validação manual** (passos na §20.6). Não foi simulado.

### 21.4 E2E real da Caixa — imóvel 633 (inspeção, sem nova análise)
- `OPENAI_API_KEY` presente e `LLM_MODEL=gpt-4o-mini` (LLM configurado).
- Imóvel 633 (COND PARQUE ARVOREDO RESIDENCIAL CLUBE): histórico **V1–V9
  preservado**; Checklist V9 = **10 CONFIRMADO / 17 PENDENTE** (27); Veredito V9 com
  **18 pendências** e **34 evidências** legíveis — coerente com `IMPLEMENTATION-REFERENCE`
  §14 e §15.
- **Nenhuma nova análise real foi executada.** A V9 real já existe e comprova o fluxo
  ponta a ponta; re-executar criaria uma V10, gastaria tokens pagos e alteraria dados
  reais sem necessidade — contrariando a diretriz de não repetir análises reais.

### 21.5 Correções desta campanha
- Único defeito reproduzido: seleção **não-determinística** do leilão corrente
  (`prop.auctions[-1]`), corrigido no commit `788d749` com helper
  `services.current_auction` (maior `id`) e teste de regressão multi-leilão. Nenhum
  defeito novo foi reproduzido nesta rodada de fechamento.

### 21.6 Critérios de encerramento
| Critério | Situação |
|---|---|
| Testes atuais aprovados (backend/frontend/tsc) | **Atendido** (527/2 skip; 90; tsc OK) |
| Fluxo financeiro de **navegador** validado | **NÃO atendido** (sem automação de navegador; validação manual pendente) |
| Análise real revalidada **ou** limitações registradas | **Atendido por registro** (V9 real inspecionada e consistente; nova análise não executada por decisão) |
| Documentação fiel às evidências | **Atendido** (esta seção) |

**Conclusão:** o MVP **NÃO** é declarado encerrado nesta rodada. Pendência
impeditiva única: **validação E2E do fluxo financeiro em navegador real** (§20.6).


---

## 22. INTEGRAÇÃO JURÍDICA E2E — Judicial API no dossiê do imóvel — 30/09/2026

Integra o resultado da Judicial API (já existente) ao dossiê jurídico, de forma
rastreável e sem reimplementar provider/DataJud/SignalEngine. Reutiliza
`judicial_client`, `judicial_integration`, SignalEngine (judicial_api), RiskEngine,
VerdictEngine e a reanálise incremental. Histórico preservado.

### 22.1 O que foi implementado
- **Correlação determinística imóvel×processo** (`backend/app/legal_correlation.py`,
  pura, sem LLM): `ALTA` (CPF/CNPJ exato), `MEDIA` (nome + comarca/UF, sem
  identificador), `BAIXA` (só nome — possível homônimo), `NAO_CONFIRMADA` (dados
  insuficientes). Regra central: **nome igual nunca confirma identidade**.
- **Classificação do vínculo** (migration `0013_processo_correlacao`): colunas
  `legal_processes.link_origin` (AUTOMATICA/MANUAL/VALIDADA/NAO_CONFIRMADA) e
  `correlation_level` (ALTA/MEDIA/BAIXA/NAO_CONFIRMADA), nullable e reversíveis.
- **Persistência enriquecida** (`judicial_integration.py`): cada processo da
  Judicial API recebe `correlation_level` + `link_origin=AUTOMATICA`; o sinal
  (Evidence JURIDICO) passa a ser **vinculado ao processo** via `EvidenceLink`; o
  resultado reporta `processes_relevant` (ALTA/MEDIA).
- **Elo sinal → checklist**: sinal patrimonial (PENHORA/ARRESTO/INDISPONIBILIDADE/
  HIPOTECA/ALIENACAO_FIDUCIARIA/PROPERTY_*) marca `PENHORA_INDISPONIBILIDADE` ou
  `ACAO_QUESTIONAMENTO` como **ATENCAO** (diligência), com `ChecklistEvidence`,
  **nunca CONFIRMADO** (evidência processual não confirma gravame). Confirmação
  manual (CONFIRMADO/NAO_APLICAVEL/RISCO_IDENTIFICADO) é preservada.
- **Risco jurídico**: o estado ATENCAO + evidência faz o RiskEngine (já existente)
  gerar o risco jurídico ao recalcular a versão; aparece no Veredito.
- **Seção jurídica no dossiê** (`services.juridical_overview`): processos
  encontrados/relevantes, pendências/confirmados jurídicos, correlação
  predominante, situação do imóvel (NÃO CONFIRMADA salvo confirmação manual),
  risco principal e diligência. **Impacto financeiro = NÃO QUANTIFICADO** (o
  jurídico não inventa valores; a fórmula de preço máximo não foi alterada).
- **Reanálise**: `CONSULTA_JUDICIAL_REALIZADA` e `PROCESSO_VINCULADO` entram em
  `EVENT_IMPACTS` (impact.py) → domínios juridico/checklist, reutilizando o
  IncrementalAnalysisService (sem segundo mecanismo).
- **UI** (`ProcessSection.tsx` + `services/processes.ts`): botão "Pesquisar
  processos", formulário de critérios, loading/erro, resumo de fontes/processos/
  relevantes/sinais, aviso de indisponibilidade, badge de correlação por processo,
  campo de vínculo e botão "Vincular ao imóvel".

### 22.2 Endpoints adicionados
- `POST /api/imoveis/{id}/juridico/processos/{process_id}/vincular` — classifica o
  vínculo (MANUAL/VALIDADA/NAO_CONFIRMADA), preserva a correlação determinística e
  emite `PROCESSO_VINCULADO`.
- `GET /api/imoveis/{id}/juridico/riscos` — riscos jurídicos persistidos.
- `GET /api/imoveis/{id}/juridico/evidencias` — evidências jurídicas legíveis.
- `POST /api/imoveis/{id}/processos/consultar` (já existente) passou a retornar
  `processos_relevantes`; o dossiê (`GET /api/imoveis/{id}`) passou a expor `juridico`.

### 22.3 Testes (evidência real, PostgreSQL real, sem LLM/DataJud real)
- `tests/test_legal_correlation.py` (12), `tests/test_juridico_integracao_e2e.py`
  (3), `tests/test_juridico_e2e_http.py` (6) — fluxo completo mock→processo→
  correlação→sinal→checklist→risco→veredito; confirmação manual preservada;
  homônimo tratado; validações 400/404.
- **Suíte backend completa: 547 passed, 2 skipped, 0 falhas** (2 skips = DataJud
  real gated). **Frontend: tsc OK; vitest 99 passed (16 arquivos)**, ProcessSection
  com 9 testes.
- **Imóvel real 633 intacto**: 9 análises (V1–V9) preservadas, nenhum processo
  criado, nenhum dado alterado. Nenhuma análise LLM/V10 executada.

### 22.4 Limitações / decisões
- `Property` não guarda CPF/CNPJ do proprietário estruturado hoje; o perfil usa
  `PropertyRegistration.holder`/`comarca` + cidade/UF. Sem identificador, a
  correlação por nome fica em MEDIA/BAIXA (nunca ALTA) — por desenho.
- A consulta real ao DataJud permanece gated (mocks nos testes).
- O fluxo financeiro **não** foi alterado; o jurídico só sinaliza risco/pendência.


---

## 23. TASK 75 — FECHAMENTO FUNCIONAL DO PRODUTO — 01/10/2026

Transforma o Radar de "módulos parcialmente expostos" em produto navegável de
ponta a ponta, reutilizando os engines/seções existentes (sem nova arquitetura,
sem reabrir Finance/Risk/Verdict/Checklist). Histórico preservado.

### 23.1 Hubs globais (nenhum menu placeholder)
Os 10 menus que eram placeholder (`FoundationPage`/`EmptyState`) viraram hubs reais
que agregam os dados e levam ao imóvel: **Dashboard** (KPIs, pipeline, alertas),
**Documentos**, **Jurídico**, **Financeiro**, **Mercado**, **Ocupação**,
**Checklist**, **Riscos**, **Veredito**, **Histórico**. **Imóveis** já era funcional
e **Leiloeiros** é novo. Novos endpoints de agregação em `main.py` reutilizam
`build_finance`, `juridical_overview`, Risk/Verdict persistidos: `/api/dashboard`,
`/api/imoveis-resumo`, `/api/financeiro`, `/api/juridico`, `/api/riscos`,
`/api/veredito`, `/api/mercado`, `/api/ocupacao`, `/api/documentos`,
`/api/historico`, `/api/checklist-global`. Números sempre de fonte determinística.

### 23.2 Domínio Leiloeiros (novo)
Modelos `Auctioneer`, `PortalAccess`, `AuctioneerDocument` + `auctions.auctioneer_id`
(FK opcional; o texto `auctioneer` é preservado como histórico). Migration
`0014_leiloeiros` (reversível). Endpoints: CRUD de leiloeiro, portais/acessos,
documentos e associação ao leilão (`POST /api/imoveis/{id}/leilao/leiloeiro`).

**Segurança da credencial** (§19/§23 da task): a senha do portal fica em coluna
separada (`portal_accesses.secret`) e **nunca** é retornada em listagens/detalhe
(só `has_secret`), nem em logs. A recuperação exige um endpoint dedicado e
auditável (`GET /api/leiloeiros/{id}/portais/{portal_id}/credencial`), que registra
o acesso sem gravar o valor. Testes de não exposição cobrem isso.

### 23.3 Break-even (Finance Engine)
`finance.py::calculate_break_even`: preço mínimo de saída (venda) para resultado
líquido zero, considerando os custos de saída parametrizados. Fórmula documentada
(base VENDA: `CT/(1-c-t)`; base GANHO: `CT*(1-t)/(1-c-t)`; denominador ≤ 0 ⇒
indefinido). Exposto no payload de `GET /api/imoveis/{id}/financeiro` e na
`FinancialSection` (com margem de segurança). Determinístico, sem LLM, com teste.

### 23.4 Identidade visual
Nova paleta (grafite `#101820` / azul petróleo `#0F4C5C` / cobre `#E07A2D` + verde/
amarelo/vermelho de status) nos tokens CSS e nos hardcodes da sidebar/topbar/cards.
Removida a marca "FUNDAÇÃO / Estrutura inicial" do `PageContainer`.

### 23.5 Testes (evidência real, PostgreSQL real, sem LLM/DataJud real)
- Backend: **558 passed, 2 skipped, 0 falhas** (de 547 → +11 da Task 75). Novos em
  `tests/test_task75_backend.py` (break-even, leiloeiro/portal/credencial,
  não-exposição de senha, hubs, associação).
- Frontend: `tsc --noEmit` OK; `vitest run` = **106 passed (18 arquivos)**, incluindo
  `hubs.test.tsx` (3) e `AuctioneersPage.test.tsx` (4, com não-exposição de senha).
- **Imóvel 633 intacto**: 9 análises (V1–V9) preservadas; nenhuma V10/análise LLM.
  0 imóveis de teste e 0 leiloeiros residuais no banco (fixtures com rollback).

### 23.6 Pendência impeditiva (declarada, não simulada)
- **E2E de navegador (Playwright) — NÃO executado**: o projeto não possui Playwright/
  Cypress e não há ambiente de browser automation aqui. Os fluxos §24/§25 da task
  (Financeiro e menus no navegador) permanecem como validação **manual**. Os testes
  HTTP/jsdom não contam como prova de E2E de navegador.
- Operacional: o container `frontend`/`backend` em execução precisa de rebuild para
  servir a nova UI/API (a validação desta task rodou em container efêmero sobre o
  código do host). Nenhum dado de produção foi alterado.

### 23.7 Lacunas reais / Fase 2
- Documentos do leiloeiro: metadados cadastrados; upload binário reutiliza a infra
  documental existente de imóveis (não há upload binário dedicado do leiloeiro
  nesta task — registrado como evolução).
- Cenários financeiros configuráveis e aluguel/yield seguem conforme o engine atual.
- Edição de portal/credencial e documentos via UI do leiloeiro: cadastro entregue;
  edição avançada é evolução.


## 24. TASK 75.1 — CORREÇÕES FINAIS DE SEGURANÇA, UI E VALIDAÇÃO — 20/09/2026

Fechamento dos GAPs levantados sobre a Task 75, sem alterar arquitetura/engines nem
as 27 canonical keys. Imóvel 633 permanece intacto (V1–V9, sem V10, sem LLM).

### 24.1 GAP 1/2 — Credencial de portal nunca em texto puro (criptografia reversível)
Antes, `portal_accesses.secret` era gravado como texto puro (apenas omitido das
respostas). Agora a credencial é **cifrada** antes de persistir e só é decifrada sob
demanda no endpoint protegido.

- **Mecanismo**: Fernet (AES-128-CBC + HMAC) da biblioteca `cryptography==44.0.0`.
  Escolhido por ser criptografia **reversível** — o app precisa recuperar a senha para
  uso, então hash irreversível não serve. Descartados AWS Secrets Manager/Vault/Redis
  (proibidos pela task; MVP local-first).
- **Chave fora do banco**: `PORTAL_SECRET_KEY` vem do ambiente (`.env`/compose), nunca
  versionada nem gravada no banco. Aceita uma chave Fernet pronta OU uma passphrase
  (derivada por SHA-256). Implementação em `backend/app/secrets_crypto.py`
  (`encrypt_secret`/`decrypt_secret`/`is_configured`), valor persistido com prefixo
  `enc:v1:`.
- **Falha fechada**: sem `PORTAL_SECRET_KEY`, o backend **recusa** salvar a credencial
  (HTTP 503) em vez de guardar texto puro. `decrypt_secret` retorna `None` para valores
  sem o prefixo (não vaza eventual legado em claro).

### 24.2 Endpoint de recuperação protegido e auditável
`GET /api/leiloeiros/{id}/portais/{portal_id}/credencial` agora exige o header
`X-Portal-Admin-Token` igual a `PORTAL_ADMIN_TOKEN` (ambiente). Falha fechada: sem o
token configurado → **503**; token ausente/errado → **401**. Registra evento de
auditoria sem gravar o valor do segredo. O payload comum continua expondo apenas
`{"has_secret": true}` — nunca `{"secret": "..."}`.

### 24.3 GAP 3 — UI de Leiloeiros completa + associação ao leilão
- `AuctioneersPage`: edição de leiloeiro, **edição de portal** (`PATCH .../portais/{id}`,
  troca opcional da credencial — sempre cifrada), e UI de **documentos** (vincular).
- A recuperação da credencial na UI pede o token de administração e o envia no header.
- **Associação leiloeiro↔leilão** (`AuctionNoticeSection`): seletor de leiloeiro
  cadastrado + ação "Associar ao leilão" (`POST /api/imoveis/{id}/leilao/leiloeiro`),
  preservando o texto histórico `auctioneer`.
- Novo endpoint backend `PATCH /api/leiloeiros/{id}/portais/{portal_id}`
  (`update_portal_access`) + schema `PortalAccessUpdate`.

### 24.4 Testes (evidência real, PostgreSQL real, sem LLM/DataJud real)
- **Backend: 562 passed, 2 skipped, 0 falhas** (558 → +4 testes de segurança 75.1 em
  `tests/test_task75_backend.py`): secret persistido cifrado (prefixo `enc:v1:`, sem o
  texto puro no banco), reveal sem token → 401, reveal sem proteção configurada → 503,
  `PATCH` de portal com troca de credencial cifrada.
- **Frontend: `tsc --noEmit` OK; `vitest run` = 108 passed (18 arquivos)**. Novos/ajustes:
  `AuctioneersPage.test.tsx` (reveal exige token no header; sem token não chama o
  endpoint) e `AuctionNoticeSection.test.tsx` (associação de leiloeiro ao leilão).
- **E2E HTTP sobre o stack vivo** (não é navegador): criar leiloeiro+portal → a
  listagem **não** contém a senha; reveal **sem** token → 401; reveal **com** token →
  200 devolvendo a senha decifrada.
- **Imóvel 633 intacto**: `checklist_executions` V1–V9 (exatamente 9), `verdicts`
  máx=9/9 distintas, `financial_analyses` máx=9/9. Nenhuma V10, nenhuma análise LLM
  nova. Artefato de verificação (1 leiloeiro) removido → 0 residuais.

### 24.5 Containers / migrations
`docker compose build backend frontend` (imagem backend agora inclui `cryptography`),
`docker compose up -d`. Health: backend `/health` ok, frontend HTTP 200. Migrations em
`0014_leiloeiros` (head == current). `.env.example` e `docker-compose.yml` documentam
`PORTAL_SECRET_KEY` e `PORTAL_ADMIN_TOKEN`.

### 24.6 E2E de navegador (Playwright) — NÃO executado (limitação declarada)
O projeto continua sem Playwright/Cypress e o ambiente não dispõe de browser
automation. Os fluxos de navegador permanecem como validação **manual**; os testes
HTTP/jsdom acima não contam como prova de E2E de navegador. (Não foi simulado.)

### 24.7 Limitação de MVP (declarada)
A proteção do endpoint de recuperação usa um token de operação único
(`PORTAL_ADMIN_TOKEN`), não um controle de acesso por usuário/perfil (não há camada de
autenticação de usuários no projeto). É suficiente para o MVP local e falha fechada;
autenticação/autorização por usuário fica como evolução (ver EVOLUTION-BACKLOG).

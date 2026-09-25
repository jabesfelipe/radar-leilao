# Radar Leilão — Controle Central do Projeto

> Documento operacional central do desenvolvimento.  
> Última consolidação: 24/09/2026 — após auditoria da TASK 67 e definição da TASK 68
> Branch principal: `main`  
> Repositório: `jabesfelipe/radar-leilao`

## 1. Objetivo

O Radar Leilão é um MVP local-first para análise rastreável de imóveis em **leilões extrajudiciais**, com imóvel como entidade central, documentos/evidências como fonte de verdade, análise incremental, histórico e memória estruturada.

A especificação arquitetural oficial permanece em:

- `docs/SPEC-VIBE-CODING-RADAR-LEILAO.md`

Este documento controla o **andamento de implementação**, registra o que já foi validado e aponta a próxima tarefa.

---

## 2. Regra de desenvolvimento

Fluxo oficial:

1. Kiro lê este arquivo.
2. Kiro executa **somente a próxima TASK marcada como PENDENTE**.
3. Kiro implementa e cria commit.
4. Usuário informa: **"da pull"**.
5. O assistente consulta o GitHub, compara o commit com o último estado aprovado e revisa o código alterado.
6. Se houver problema, é criada correção antes de avançar.
7. Se estiver correto, a TASK recebe **[x] CONCLUÍDA** neste documento.
8. O próximo item pendente vira a próxima instrução operacional para o Kiro.
9. Cada avanço de tarefa deve deixar um commit rastreável.

### Critério de aprovação

Uma TASK só é considerada concluída quando:

- o código implementa o escopo solicitado;
- não inventa regra de negócio;
- não cria enum/regra/campo não suportado pela SPEC ou contrato existente;
- testes/build relevantes passam;
- não há regressão evidente;
- o escopo negativo da TASK foi respeitado;
- o commit é identificável.

---

## 3. Estado atual

**Último commit de implementação:** `24e6b2b`  
**Último commit de documentação:** `e0f3b5ac63686e0849687d95143d70bb2f951015`  
**Mensagem:** `docs: registra auditoria task 66 e define task 67`

**Última TASK aprovada:** TASK 67

**TASK 65:** 🟢 CONCLUÍDA — Document Intelligence + RAG direcionado.

**TASK 65.1:** 🟢 CONCLUÍDA E APROVADA — OCR operacional no Docker e telemetria do retrieval direcionado.

**TASK 66:** 🟢 CONCLUÍDA E APROVADA — embeddings dos novos DocumentChunks integrados à ingestão, com prova real de recuperação vetorial no imóvel 633.

**TASK 67:** 🟢 CONCLUÍDA E APROVADA — diagnóstico real do contexto RAG no V7. Foi comprovada falha de retrieval: o edital não coexistia com a matrícula no contexto dos agentes. Nenhuma alteração funcional foi feita, conforme escopo diagnóstico.

**TASK 68:** 🟡 PENDENTE — correção mínima para tornar edital + matrícula recuperáveis em conjunto no imóvel 633, seguida de validação E2E final.

**Status global:** 🟡 MVP em fechamento técnico — núcleo funcional operacional; falha de contexto RAG do edital identificada e isolada; resta uma correção controlada antes da validação final e encerramento do MVP.

> A porcentagem de conclusão não é usada como fonte oficial. O controle por TASK abaixo é a referência.

# 4. Backlog controlado

As TASKs 01–50 permanecem concluídas conforme histórico abaixo e na documentação anterior.

## TASK 51 — Primeiro teste E2E com imóvel real da Caixa
- [~] EXECUÇÃO DIAGNÓSTICA REALIZADA — NÃO CONCLUÍDA
- Commit: `ea7db957b6ef6e739bfa19d086b4a508d462acc6`

## TASK 51B — Reexecução controlada do E2E após preparar runtime
- [x] CONCLUÍDA
- Runtime oficial WSL2 → Docker → PostgreSQL + pgvector validado.
- Migrations executadas e validadas em banco limpo.

## TASK 52 — Correção e validação da cadeia de migrations
- [x] CONCLUÍDA
- Commit de implementação: `b676a889fdfb79c4609b72107a345f9b5ed3a080`
- Validação em banco limpo: migrations 0001 → 0008.
- Resultado: 211 passed, 10 failed; falhas restantes eram de aplicação.

## TASK 53 — Corrigir snapshot anterior do Checklist
- [x] CONCLUÍDA
- Commit: `f36cecebb490112945d2f6a91ae96bf2e9492157`
- Auditoria: 🟢 aprovada.

## TASK 54 — Reexecutar suíte e corrigir a próxima falha
- [x] CONCLUÍDA
- Commit: `ecde86518d4d9d4136184877974f103b9735e80d`
- Resultado: 213 passed, 8 failed.

## TASK 55 — Corrigir a próxima falha da suíte
- [x] CONCLUÍDA
- Commit: `27a65e3cd21053d710c68338a4f1a853a4ad8caa`
- Resultado: 214 passed, 7 failed.

## TASK 56 — Corrigir a próxima falha da suíte
- [x] CONCLUÍDA
- Commit: `1aa3912445c3e25a6f0b9e2ac4fa93d9e82f1d74`
- Resultado: 215 passed, 6 failed.

## TASK 57 — Corrigir a próxima falha da suíte
- [x] CONCLUÍDA
- Commit: `4c26ee67243cc622b89748a607fc01e3e294ca26`
- Auditoria: 🟢 aprovada.
- Corrigida a fixture de `test_extraction.py` para fornecer `success=True`.
- Resultado: 216 passed, 5 failed.

## TASK 58 — Corrigir a próxima falha de integração
- [x] CONCLUÍDA
- Commit: `23b47172f1855e7f6facde86142ed7762759615c`
- Auditoria: 🟢 aprovada.
- Falha reproduzida inicialmente como `Decimal is not JSON serializable`, mas o traceback completo confirmou a causa real: o PATCH do Checklist retornava `{}`.
- Causa raiz: `update_checklist` fazia `db.commit(); return result` sem `db.refresh(result)`; após o commit, os atributos ORM expiravam e a serialização retornava objeto vazio.
- Correção: uma única linha em `main.py`, adicionando `db.refresh(result)` antes do retorno.
- Contrato preservado; não houve alteração de schema, migration, teste, regra de negócio ou conversão indevida para string.
- Resultado: teste alvo passou; `test_integration_flows.py`: 12 passed, 4 failed; suíte: 217 passed, 4 failed.

---

# 5. Últimas TASKs — concluídas

## TASK 59 — Corrigir a primeira falha real do fluxo de análise
- [x] CONCLUÍDA
- Commit: `92c3e44aa314fc38c402a895d64b9add17381d85`
- Correção: serialização do resultado financeiro antes da criação do veredito.
- Auditoria: 🟢 aprovada.

## TASK 60 — Corrigir as 3 falhas restantes da integração
- [x] CONCLUÍDA
- Commit: `1262637fa681d056f4191a8e15cbb72aefcc4038`
- Auditoria: 🟢 aprovada por inspeção do diff.
- `get_property`: análises agora são expostas ordenadas por versão.
- `create_analysis`: próxima versão agora é calculada diretamente no banco, corrigindo a reanálise incremental (v1, v2...).
- Sem migration/schema, alteração de testes, nova regra de negócio ou refatoração ampla.
- CI/workflow: nenhuma execução publicada no GitHub para este commit; portanto não há contagem independente de testes a registrar.

## TASK 61 — Setup local automatizado (WSL2 + Docker)
- [x] CONCLUÍDA
- Commit: `f7a0e25a38d3a037a2513c87a4290b2ea3687291`
- `docker-compose.yml` (postgres + backend + frontend), Dockerfiles, entrypoint com `alembic upgrade head`, scripts em `scripts/`, `docs/LOCAL-SETUP.md`.
- Stack validada ao vivo: 3 serviços saudáveis, migrations automáticas, `pytest -q` = 221 passed.

## TASK 62 — Cadastro completo do imóvel de leilão
- [x] CONCLUÍDA
- Cadastro guiado (wizard 5 etapas) conectado ao fluxo de análise existente; nenhum fluxo de IA recriado.
- Backend: migration `0009_cadastro_completo_imovel` (colunas físicas/origem em `properties`, 1º/2º leilão em `auctions`, `item` em `auction_notices`, nova tabela `property_sources`); endpoint transacional `POST /api/imoveis/completo`; `GET/POST /api/imoveis/{id}/fontes`; `get_property` expõe edital/matrícula/fontes.
- Frontend: `PropertyWizard`, `PropertiesPage` reescrito, dossiê enriquecido (Visão geral + seção Leilão real).
- Fixture de validação: COND PARQUE ARVOREDO RESIDENCIAL CLUBE (E2E real da Caixa NÃO declarado concluído).
- Resultado: `pytest -q` = **227 passed** (+6); Vitest = 88 passed; `alembic upgrade head` aplica 0009 em banco limpo.

## TASK 63 — Ajustes finais do cadastro: data/hora do leilão e feedback de upload
- [x] CONCLUÍDA
- Data + hora do 1º/2º leilão preservadas: `auctions.first/second_auction_date` `DATE` → `TIMESTAMP` (migration `0010_leilao_data_hora`; ajuste na redução de `0001` para funcionar em banco novo).
- Feedback de upload no wizard: falha de upload não é mais silenciosa — imóvel é criado, o usuário vê quais documentos falharam e vai ao Dossiê por ação própria.
- Fluxo de análise intacto. Nenhuma nova tabela/arquitetura.
- Resultado: `pytest -q` = **228 passed** (+1); Vitest = **89 passed** (+1); `tsc` OK; `alembic upgrade head` validado em banco existente e limpo.

## TASK 64 — Operação segura local: rebuild, .env, logs e proteção de dados
- [x] CONCLUÍDA
- `start.sh`/`restart.sh` com `up -d --build` (imagem atual) preservando `postgres_data`/`backend_storage`; `restart` recarrega o `.env`.
- Novo `scripts/logs.sh` (status/tail/follow/save→`logs/`); rotação de logs no compose (`json-file` 10m×5); `LOG_LEVEL` no backend.
- Logging detalhado do backend (cadastro, documentos, RAG, LangGraph, agentes, LLM) sem vazar segredos (`sanitize_error`, sem conteúdo de documento).
- `.gitignore`: `logs/`, `backups/`. Novo `docs/OPERATIONS.md`.
- Sem mudança de schema (nenhuma migration nova). Dados preservados no rebuild/restart (contagem idêntica antes/depois). `OPENAI_API_KEY configurada` confirmado sem exibir a chave.
- Resultado: `pytest -q` = **228 passed** (sem regressão); `health.sh` 5/5 OK.

**Status global:** 🟢 suíte automatizada verde; 🟡 E2E real em execução diagnóstica com LLM. O fluxo LLM/RAG/LangGraph/Agentes está funcionando, mas a cobertura documental da matrícula e do retrieval do Checklist precisa ser corrigida antes de declarar o E2E completo.


---

# 6. Consolidação de validação — 21/09/2026

## Suíte de integração

```text
pytest -q tests/test_integration_flows.py
16 passed, 2110 warnings in 3.29s
```

## Suíte completa

```text
pytest -q
221 passed, 2744 warnings in 9.41s
```

### Interpretação

- 221/221 testes passaram.
- 16/16 testes de integração passaram.
- 3/3 testes direcionados da Task 60 passaram.
- Não há falha automatizada conhecida neste estado.
- Os warnings foram registrados, mas não são tratados como falhas nesta etapa.

## Documentação consolidada

A especificação mestre foi movida para:

`docs/SPEC-VIBE-CODING-RADAR-LEILAO.md`

A especificação foi atualizada para refletir a stack efetivamente adotada pelo projeto, removendo a referência residual a Java/Spring e mantendo **Python + FastAPI** como backend oficial.

## Próximo marco

A próxima etapa não é criar uma nova TASK de correção preventiva.

O próximo marco é validar o fluxo real com imóveis e documentos reais, especialmente:

- edital;
- matrícula;
- normalização;
- OCR quando necessário;
- evidências;
- RAG;
- análise;
- checklist;
- riscos;
- Veredito;
- histórico/reanálise.

A ausência de chave de LLM e as limitações observadas no processamento do documento escaneado da matrícula da Caixa devem continuar registradas como limitações do E2E real, e não como falhas da suíte automatizada.
# Radar Leilão — Controle Central do Projeto

> Documento operacional central do desenvolvimento.  
> Última consolidação: 21/09/2026  
> Branch principal: `main`  
> Repositório: `jabesfelipe/radar-leilao`

## 1. Objetivo

O Radar Leilão é um MVP local-first para análise rastreável de imóveis em **leilões extrajudiciais**, com imóvel como entidade central, documentos/evidências como fonte de verdade, análise incremental, histórico e memória estruturada.

A especificação arquitetural oficial permanece em:

- `docs/SPEC-VIBE-CODING-RADAR-LEILAO.md`

Este documento controla o **andamento de implementação**, registra o que já foi validado e aponta a próxima tarefa.

---

## 2. Regra de desenvolvimento

Fluxo oficial:

1. Kiro lê este arquivo.
2. Kiro executa **somente a próxima TASK marcada como PENDENTE**.
3. Kiro implementa e cria commit.
4. Usuário informa: **"da pull"**.
5. O assistente consulta o GitHub, compara o commit com o último estado aprovado e revisa o código alterado.
6. Se houver problema, é criada correção antes de avançar.
7. Se estiver correto, a TASK recebe **[x] CONCLUÍDA** neste documento.
8. O próximo item pendente vira a próxima instrução operacional para o Kiro.
9. Cada avanço de tarefa deve deixar um commit rastreável.

### Critério de aprovação

Uma TASK só é considerada concluída quando:

- o código implementa o escopo solicitado;
- não inventa regra de negócio;
- não cria enum/regra/campo não suportado pela SPEC ou contrato existente;
- testes/build relevantes passam;
- não há regressão evidente;
- o escopo negativo da TASK foi respeitado;
- o commit é identificável.

---

## 3. Estado atual
**Último commit de implementação:** `1262637fa681d056f4191a8e15cbb72aefcc4038`  
**Último commit de documentação:** `e59d8613a994ad4834b94fe96321346aff6ebb20`  
**Mensagem:** `fix: corrige 3 falhas restantes da integracao`

**Última TASK aprovada:** TASK 60

**TASK 59:** 🟢 CONCLUÍDA — primeira falha do fluxo de análise corrigida e auditada.

**TASK 60:** 🟢 CONCLUÍDA — três falhas restantes da integração corrigidas e auditadas por inspeção do diff. O GitHub não publicou workflow/CI para o commit.

**TASK 51:** execução diagnóstica realizada, não aprovada como E2E completo.

**TASK 51B:** runtime WSL + Docker + PostgreSQL/pgvector preparado; migrations corrigidas e validadas.

**TASK 52:** cadeia de migrations validada em banco limpo; 211 testes passaram e 10 falharam por problemas de aplicação fora do escopo da migration.

**TASK 53:** correção do snapshot anterior do Checklist aprovada.

**TASK 54:** concluída — fixture de `test_documents.py` corrigida; 213 passed, 8 failed.

**TASK 55:** concluída — fixture de `test_extraction.py` corrigida; 214 passed, 7 failed.

**TASK 56:** concluída — fixture de `test_extraction.py` corrigida; 215 passed, 6 failed.

**TASK 57:** concluída — fixture de `test_extraction.py` corrigida; 216 passed, 5 failed.

**TASK 58:** concluída — corrigido `db.refresh(result)` no endpoint `update_checklist`; 217 passed, 4 failed.

**Última validação:** suíte completa verde — 221 passed.

**Status global:** 🟡 MVP em construção.

> A porcentagem de conclusão não é usada como fonte oficial. O controle por TASK abaixo é a referência.

---

# 4. Backlog controlado

As TASKs 01–50 permanecem concluídas conforme histórico abaixo e na documentação anterior.

## TASK 51 — Primeiro teste E2E com imóvel real da Caixa
- [~] EXECUÇÃO DIAGNÓSTICA REALIZADA — NÃO CONCLUÍDA
- Commit: `ea7db957b6ef6e739bfa19d086b4a508d462acc6`

## TASK 51B — Reexecução controlada do E2E após preparar runtime
- [x] CONCLUÍDA
- Runtime oficial WSL2 → Docker → PostgreSQL + pgvector validado.
- Migrations executadas e validadas em banco limpo.

## TASK 52 — Correção e validação da cadeia de migrations
- [x] CONCLUÍDA
- Commit de implementação: `b676a889fdfb79c4609b72107a345f9b5ed3a080`
- Validação em banco limpo: migrations 0001 → 0008.
- Resultado: 211 passed, 10 failed; falhas restantes eram de aplicação.

## TASK 53 — Corrigir snapshot anterior do Checklist
- [x] CONCLUÍDA
- Commit: `f36cecebb490112945d2f6a91ae96bf2e9492157`
- Auditoria: 🟢 aprovada.

## TASK 54 — Reexecutar suíte e corrigir a próxima falha
- [x] CONCLUÍDA
- Commit: `ecde86518d4d9d4136184877974f103b9735e80d`
- Resultado: 213 passed, 8 failed.

## TASK 55 — Corrigir a próxima falha da suíte
- [x] CONCLUÍDA
- Commit: `27a65e3cd21053d710c68338a4f1a853a4ad8caa`
- Resultado: 214 passed, 7 failed.

## TASK 56 — Corrigir a próxima falha da suíte
- [x] CONCLUÍDA
- Commit: `1aa3912445c3e25a6f0b9e2ac4fa93d9e82f1d74`
- Resultado: 215 passed, 6 failed.

## TASK 57 — Corrigir a próxima falha da suíte
- [x] CONCLUÍDA
- Commit: `4c26ee67243cc622b89748a607fc01e3e294ca26`
- Auditoria: 🟢 aprovada.
- Corrigida a fixture de `test_extraction.py` para fornecer `success=True`.
- Resultado: 216 passed, 5 failed.

## TASK 58 — Corrigir a próxima falha de integração
- [x] CONCLUÍDA
- Commit: `23b47172f1855e7f6facde86142ed7762759615c`
- Auditoria: 🟢 aprovada.
- Falha reproduzida inicialmente como `Decimal is not JSON serializable`, mas o traceback completo confirmou a causa real: o PATCH do Checklist retornava `{}`.
- Causa raiz: `update_checklist` fazia `db.commit(); return result` sem `db.refresh(result)`; após o commit, os atributos ORM expiravam e a serialização retornava objeto vazio.
- Correção: uma única linha em `main.py`, adicionando `db.refresh(result)` antes do retorno.
- Contrato preservado; não houve alteração de schema, migration, teste, regra de negócio ou conversão indevida para string.
- Resultado: teste alvo passou; `test_integration_flows.py`: 12 passed, 4 failed; suíte: 217 passed, 4 failed.

---

# 5. Últimas TASKs — concluídas

## TASK 59 — Corrigir a primeira falha real do fluxo de análise
- [x] CONCLUÍDA
- Commit: `92c3e44aa314fc38c402a895d64b9add17381d85`
- Correção: serialização do resultado financeiro antes da criação do veredito.
- Auditoria: 🟢 aprovada.

## TASK 60 — Corrigir as 3 falhas restantes da integração
- [x] CONCLUÍDA
- Commit: `1262637fa681d056f4191a8e15cbb72aefcc4038`
- Auditoria: 🟢 aprovada por inspeção do diff.
- `get_property`: análises agora são expostas ordenadas por versão.
- `create_analysis`: próxima versão agora é calculada diretamente no banco, corrigindo a reanálise incremental (v1, v2...).
- Sem migration/schema, alteração de testes, nova regra de negócio ou refatoração ampla.
- CI/workflow: nenhuma execução publicada no GitHub para este commit; portanto não há contagem independente de testes a registrar.

## TASK 61 — Setup local automatizado (WSL2 + Docker)
- [x] CONCLUÍDA
- Commit: `f7a0e25a38d3a037a2513c87a4290b2ea3687291`
- `docker-compose.yml` (postgres + backend + frontend), Dockerfiles, entrypoint com `alembic upgrade head`, scripts em `scripts/`, `docs/LOCAL-SETUP.md`.
- Stack validada ao vivo: 3 serviços saudáveis, migrations automáticas, `pytest -q` = 221 passed.

## TASK 62 — Cadastro completo do imóvel de leilão
- [x] CONCLUÍDA
- Cadastro guiado (wizard 5 etapas) conectado ao fluxo de análise existente; nenhum fluxo de IA recriado.
- Backend: migration `0009_cadastro_completo_imovel` (colunas físicas/origem em `properties`, 1º/2º leilão em `auctions`, `item` em `auction_notices`, nova tabela `property_sources`); endpoint transacional `POST /api/imoveis/completo`; `GET/POST /api/imoveis/{id}/fontes`; `get_property` expõe edital/matrícula/fontes.
- Frontend: `PropertyWizard`, `PropertiesPage` reescrito, dossiê enriquecido (Visão geral + seção Leilão real).
- Fixture de validação: COND PARQUE ARVOREDO RESIDENCIAL CLUBE (E2E real da Caixa NÃO declarado concluído).
- Resultado: `pytest -q` = **227 passed** (+6); Vitest = 88 passed; `alembic upgrade head` aplica 0009 em banco limpo.

## TASK 63 — Ajustes finais do cadastro: data/hora do leilão e feedback de upload
- [x] CONCLUÍDA
- Data + hora do 1º/2º leilão preservadas: `auctions.first/second_auction_date` `DATE` → `TIMESTAMP` (migration `0010_leilao_data_hora`; ajuste na redução de `0001` para funcionar em banco novo).
- Feedback de upload no wizard: falha de upload não é mais silenciosa — imóvel é criado, o usuário vê quais documentos falharam e vai ao Dossiê por ação própria.
- Fluxo de análise intacto. Nenhuma nova tabela/arquitetura.
- Resultado: `pytest -q` = **228 passed** (+1); Vitest = **89 passed** (+1); `tsc` OK; `alembic upgrade head` validado em banco existente e limpo.

## TASK 64 — Operação segura local: rebuild, .env, logs e proteção de dados
- [x] CONCLUÍDA
- `start.sh`/`restart.sh` com `up -d --build` (imagem atual) preservando `postgres_data`/`backend_storage`; `restart` recarrega o `.env`.
- Novo `scripts/logs.sh` (status/tail/follow/save→`logs/`); rotação de logs no compose (`json-file` 10m×5); `LOG_LEVEL` no backend.
- Logging detalhado do backend (cadastro, documentos, RAG, LangGraph, agentes, LLM) sem vazar segredos (`sanitize_error`, sem conteúdo de documento).
- `.gitignore`: `logs/`, `backups/`. Novo `docs/OPERATIONS.md`.
- Sem mudança de schema (nenhuma migration nova). Dados preservados no rebuild/restart (contagem idêntica antes/depois). `OPENAI_API_KEY configurada` confirmado sem exibir a chave.
- Resultado: `pytest -q` = **228 passed** (sem regressão); `health.sh` 5/5 OK.

**Status global:** 🟢 suíte automatizada verde; 🟡 base operacional pronta para o E2E real da Caixa com `OPENAI_API_KEY` (E2E ainda não executado).


---

# 6. Consolidação de validação — 21/09/2026

## Suíte de integração

```text
pytest -q tests/test_integration_flows.py
16 passed, 2110 warnings in 3.29s
```

## Suíte completa

```text
pytest -q
221 passed, 2744 warnings in 9.41s
```

### Interpretação

- 221/221 testes passaram.
- 16/16 testes de integração passaram.
- 3/3 testes direcionados da Task 60 passaram.
- Não há falha automatizada conhecida neste estado.
- Os warnings foram registrados, mas não são tratados como falhas nesta etapa.

## Documentação consolidada

A especificação mestre foi movida para:

`docs/SPEC-VIBE-CODING-RADAR-LEILAO.md`

A especificação foi atualizada para refletir a stack efetivamente adotada pelo projeto, removendo a referência residual a Java/Spring e mantendo **Python + FastAPI** como backend oficial.

## Próximo marco

A próxima etapa não é criar uma nova TASK de correção preventiva.

O próximo marco é validar o fluxo real com imóveis e documentos reais, especialmente:

- edital;
- matrícula;
- normalização;
- OCR quando necessário;
- evidências;
- RAG;
- análise;
- checklist;
- riscos;
- Veredito;
- histórico/reanálise.

A ausência de chave de LLM e as limitações observadas no processamento do documento escaneado da matrícula da Caixa devem continuar registradas como limitações do E2E real, e não como falhas da suíte automatizada.

---

# 7. Diagnóstico E2E real — imóvel Caixa 633 / análise V4

## Resultado validado em 24/09/2026

A análise real da propriedade **633** chegou à versão **4** com LLM real configurada.

Validações observadas no runtime:

- provider: OpenAI;
- modelo: `gpt-4o-mini`;
- 5 agentes executados: documental, jurídico, financeiro, mercado e checklist;
- todos os agentes receberam os mesmos 8 chunks: `276, 277, 278, 279, 280, 281, 282, 283`;
- todos os `llm_runs` da análise 189 ficaram `CONCLUIDO`;
- 31 evidências foram produzidas;
- execução do Checklist: 27 resultados;
- 2 resultados `CONFIRMADO`;
- 25 resultados `PENDENTE`;
- as duas confirmações foram `CONSOLIDACAO_REGISTRADA` e `EDITAL_LIDO`;
- as duas confirmações possuem evidência vinculada.

### Diagnóstico

O fluxo de execução e persistência está funcionando. O problema identificado não é uma falha geral do LLM, LangGraph, execução do Checklist ou persistência.

O diagnóstico aponta duas limitações de entrada/contexto:

1. **Matrícula escaneada / extração insuficiente**
   - o chunk `276`, associado à versão da matrícula, contém essencialmente os dados de autenticidade/CNS e indicação de páginas;
   - o conteúdo registral relevante da matrícula não está disponível adequadamente no chunk utilizado pela análise;
   - portanto, a análise jurídica da matrícula fica limitada.

2. **Retrieval genérico e contexto insuficiente para o Checklist**
   - os 5 agentes receberam exatamente os mesmos 8 chunks;
   - os chunks do edital recuperados são predominantemente o início do documento;
   - existem informações úteis nesses chunks, como datas dos leilões, comissão, responsabilidade por levantamento/pagamento de débitos, condições de pagamento e preço mínimo;
   - porém, um único conjunto genérico de 8 chunks não garante cobertura das 27 perguntas do Checklist Mestre;
   - não devemos transformar automaticamente `PENDENTE` em resposta sem evidência.

### Decisão técnica

A próxima tarefa deve atacar **Document Intelligence + Retrieval direcionado**, preservando integralmente os fluxos já aprovados.

---

# TASK 65 — Melhorar Document Intelligence e RAG direcionado para o Checklist

**Status:** 🟡 PENDENTE — próxima task do Kiro.

### Objetivo

Melhorar a capacidade do Radar de analisar documentos reais de leilão, especialmente PDFs escaneados e documentos extensos, sem quebrar o fluxo existente.

A tarefa deve resolver duas limitações observadas no E2E da Caixa:

1. detectar quando a normalização textual de um documento é insuficiente e permitir OCR como etapa de recuperação;
2. evitar que o Checklist Mestre dependa exclusivamente de uma única busca RAG genérica com 8 chunks para responder 27 perguntas heterogêneas.

### Princípio obrigatório

**Não preencher o Checklist artificialmente.**

Se os documentos não comprovarem uma resposta, o sistema deve manter o item pendente ou utilizar um estado já previsto pelo contrato quando houver evidência suficiente para isso. A tarefa não pode introduzir respostas inventadas, inferências sem evidência ou alteração silenciosa da semântica dos estados.

### Escopo obrigatório

#### 1. Preservar tudo que já funciona

Não alterar desnecessariamente:

- cadastro completo;
- upload;
- fluxo `POST /api/imoveis/{id}/analisar`;
- LangGraph existente;
- Document Agent;
- Jurídico Agent;
- Financeiro Agent;
- Mercado Agent;
- Checklist Agent como contrato;
- Risk Engine;
- Verdict Engine;
- histórico/reanálise;
- memória estruturada;
- frontend do Dossiê;
- migrations existentes;
- dados do imóvel 633.

Não fazer reset de banco.

Não apagar documentos/chunks/evidências existentes.

Não substituir migrations históricas.

Se houver necessidade real de schema, criar migration incremental nova e somente após justificar a necessidade.

#### 2. Diagnóstico de qualidade documental

Revisar o pipeline existente de normalização para permitir identificar documentos cujo texto extraído é insuficiente.

O mecanismo deve considerar sinais objetivos de baixa qualidade, por exemplo:
- texto vazio ou quase vazio;
- quantidade de caracteres incompatível com o número de páginas;
- documento escaneado sem camada textual;
- conteúdo repetitivo de autenticação/capa sem conteúdo principal.

**Não definir um limite arbitrário sem verificar o pipeline e os testes existentes.**

A solução deve preservar:

- documento original;
- versão;
- hash;
- páginas;
- rastreabilidade;
- chunks existentes.

#### 3. OCR

Investigar e implementar a estratégia de OCR somente onde o pipeline detectar necessidade.

Requisitos:

- OCR não deve substituir o original;
- resultado OCR deve ser rastreável ao documento/versão;
- preservar página;
- permitir identificar que o texto veio de OCR;
- não quebrar documentos que já possuem texto;
- não criar dependência externa obrigatória sem necessidade;
- manter operação local-first;
- registrar erros de OCR nos logs sem conteúdo sensível.

Se a infraestrutura atual não tiver uma solução OCR local adequada, documentar claramente a limitação em vez de inventar uma integração frágil.

#### 4. Retrieval direcionado para Checklist

Revisar o fluxo atual em que uma consulta genérica recupera um único conjunto de chunks para todos os agentes.

Para o Checklist Mestre, criar estratégia de recuperação direcionada por grupos/domínios ou por perguntas, reutilizando o RAG existente sempre que possível.

A estratégia deve:

- usar as perguntas/regras canônicas existentes;
- preservar os 27 `canonical_key`;
- gerar consultas contextualizadas;
- recuperar chunks relevantes de documentos distintos;
- deduplicar chunks;
- manter `chunk_ids`;
- preservar evidência e rastreabilidade;
- respeitar limites de contexto;
- evitar chamadas LLM desnecessárias;
- não fazer 27 chamadas independentes obrigatoriamente se uma estratégia por grupo for suficiente.

Grupos podem ser organizados por domínio/contexto existente no Checklist Mestre, mas **não criar novas regras de negócio nem alterar os 27 itens canônicos**.

#### 5. Contexto do Checklist Agent

O Checklist Agent deve receber contexto suficiente para investigar as perguntas, mas continuar obedecendo às regras atuais:

- somente keys canônicas;
- somente estados permitidos;
- evidência obrigatória quando aplicável;
- chunk/page/section/excerpt rastreáveis;
- não inventar fatos;
- manter pendente quando não houver suporte documental.

O agente não deve ser obrigado a transformar todo item em `CONFIRMADO`.

#### 6. Justificativa de pendência

Avaliar a forma atual de representar `PENDENTE`.

Sem alterar o contrato de forma ampla, garantir que o sistema consiga distinguir, quando suportado pelos modelos atuais, entre:

- informação não encontrada;
- documento não disponível;
- evidência insuficiente;
- investigação dependente de fonte externa;
- análise ainda pendente.

Se for necessária alteração de contrato/schema, **não inventar campo silenciosamente**. Primeiro verificar a SPEC e os modelos existentes e criar mudança incremental somente se realmente necessária.

#### 7. Testes

Adicionar testes focados no comportamento novo, sem remover ou enfraquecer testes existentes.

Obrigatório validar pelo menos:

- documento textual normal continua funcionando sem OCR;
- documento com extração insuficiente é detectado;
- OCR, quando disponível, preserva rastreabilidade por página;
- retrieval direcionado recupera chunks diferentes quando as perguntas exigem documentos/contextos diferentes;
- Checklist continua usando apenas canonical keys;
- evidências continuam vinculadas aos chunks corretos;
- ausência de evidência não gera confirmação artificial;
- fluxo existente de análise continua funcionando;
- migrations existentes continuam válidas;
- banco existente não é resetado.

Executar:

```bash
pytest -q
```

E, se houver testes frontend afetados:

```bash
npm test -- --run
npm run build
```

Usar os comandos efetivamente existentes no projeto, sem inventar comandos.

### Validação específica do caso Caixa 633

Depois da implementação, reexecutar a análise do imóvel 633 somente de forma controlada.

**Não apagar as versões históricas existentes.**

Validar:

- nova versão de análise;
- documentos preservados;
- chunks/evidências anteriores preservados;
- novos chunks quando OCR for necessário;
- retrieval direcionado;
- Checklist com rastreabilidade;
- Risk/Verdict sem regressão.

O resultado não precisa obrigatoriamente transformar os 27 itens em confirmados. O critério é aumentar a **cobertura investigada com evidência rastreável**, mantendo pendente aquilo que realmente não puder ser comprovado.

### Fora do escopo

- não trocar `gpt-4o-mini`;
- não trocar provider;
- não trocar LangGraph;
- não criar novos agentes;
- não refatorar toda a arquitetura de RAG;
- não criar MinIO/Redis/ELK;
- não criar infraestrutura externa obrigatória;
- não alterar Risk/Verdict;
- não alterar os 27 itens do Checklist Mestre;
- não criar respostas determinísticas artificiais;
- não resetar banco;
- não apagar histórico;
- não apagar documentos;
- não alterar migrations históricas;
- não fazer alteração manual de dados para "melhorar" o resultado.

### Critério de aceite

A TASK 65 somente poderá ser considerada concluída quando:

1. o pipeline identificar adequadamente extração textual insuficiente;
2. houver estratégia segura para OCR quando aplicável, ou limitação explicitamente documentada se a implementação local não for viável;
3. o Checklist utilizar retrieval direcionado em vez de depender exclusivamente da busca genérica única;
4. evidências permanecerem rastreáveis até documento/versão/chunk/página/seção quando disponíveis;
5. nenhum item for confirmado sem suporte documental;
6. dados existentes forem preservados;
7. `pytest -q` passar sem regressão;
8. build/testes frontend relevantes passarem, quando afetados;
9. o caso Caixa 633 puder ser reanalisado sem apagar versões anteriores;
10. a implementação ficar limitada ao escopo desta TASK.

### Fluxo esperado após a TASK

```
Documento original
      ↓
Normalização
      ↓
Texto suficiente?
   ┌──┴──┐
  SIM   NÃO
   │     │
   │    OCR
   │     │
   └──┬──┘
      ↓
Chunks rastreáveis
      ↓
RAG
      ↓
Retrieval direcionado
      ↓
Checklist / Agentes
      ↓
Evidências
      ↓
Risk
      ↓
Verdict
      ↓
Histórico
```

### Regra de execução para o Kiro

**Executar somente a TASK 65.**

Não antecipar TASK 66.

Antes de qualquer alteração destrutiva, fazer backup e confirmar o estado do banco.

Ao finalizar:

- criar commit único e rastreável;
- informar arquivos alterados;
- informar testes executados;
- informar resultado do caso Caixa 633;
- não declarar E2E completo sem validação real;
- aguardar auditoria antes de avançar.
- docs/OPERATIONS.md
- docs/LOCAL-SETUP.md


---

## TASK 65 — Document Intelligence e RAG direcionado para o Checklist

- [x] CONCLUÍDA
- Encerrada após a TASK 65.1.
- Commit: `f8c21bf7f65659e580a0ab152956c6567b9d092a`
- Auditoria: 🟡 implementação aprovada estruturalmente, mas **TASK 65 não foi encerrada**.

### Resultado da auditoria
- A detecção de extração insuficiente foi implementada e usa o `extraction_metadata` existente, sem migration.
- O RAG direcionado reutiliza o `HybridRetriever`, deduplica chunks, preserva `chunk_id` e entrega contexto direcionado somente ao Checklist Agent.
- Os 27 canonical keys, estados e regras de evidência do Checklist foram preservados.
- A suíte reportada pelo Kiro foi `pytest -q = 239 passed`; o GitHub não publicou workflow/CI para este commit, portanto o número não foi validado independentemente por CI.
- E2E 633 gerou V5 preservando V1–V4. Checklist V5 ficou com 3 CONFIRMADO e 24 PENDENTE; Risk/Verdict permaneceram funcionando.

### Pontos que impedem o encerramento
1. **OCR não está operacional no Docker:** `ocr_available()=False`; o `backend/Dockerfile` não instala Tesseract/Poppler e `backend/requirements.txt` não possui as dependências Python do OCR. A matrícula escaneada continua sem OCR real.
2. **Custo/latência do retrieval:** a implementação gera um embedding por item do Checklist, potencialmente 27 embeddings por análise. Isso não são 27 chamadas de geração do LLM, mas deve ser medido e documentado antes do encerramento.

### Preservação validada
- Não houve migration nova.
- Não houve reset de banco.
- V1–V4 permaneceram preservadas.
- O fluxo dos cinco agentes continuou funcionando.
- O Checklist permaneceu conservador, sem confirmação artificial.

### TASK 65.1 — Tornar OCR operacional e validar E2E da matrícula
- [x] CONCLUÍDA — aprovada em auditoria.
- Objetivo: provisionar OCR local no Docker, validar Tesseract + português + Poppler/pytesseract, reprocessar a matrícula do imóvel 633 sem apagar a versão anterior, executar nova análise, validar rastreabilidade por página/evidência e medir a quantidade de embeddings do RAG direcionado.
- Não alterar os 27 itens, Risk/Verdict, provider/modelo, histórico ou dados existentes.
- Não fazer otimização ampla do RAG nesta TASK; primeiro medir o comportamento atual.
- Se houver qualquer alteração de schema, somente migration incremental e somente se indispensável.
- Ao finalizar, criar um único commit, atualizar este documento com resultados reais e aguardar auditoria.

**Próxima ação operacional:** Kiro deve executar **somente TASK 66**.
- **Frente A:** detecção objetiva de extração insuficiente em `backend/app/documents/normalizer.py` (`assess_extraction_quality`: `char_count`/`original_bytes`/`chars_per_kb`/`is_binary`/`extraction_quality` gravados no `extraction_metadata`, sem coluna nova); OCR local-first **opcional** em `backend/app/documents/ocr.py` (import-guard `pytesseract`/`pdf2image`) — **indisponível neste ambiente** (dependências de sistema não provisionadas), pipeline preparado e limitação documentada.
- **Frente B:** RAG direcionado por item do Checklist em `backend/app/rag/checklist_retrieval.py` (query derivada de `question`/`description`/`expected_evidence`/`related_rules`), reutilizando o `HybridRetriever` existente, com dedup por `chunk_id`, rastreabilidade (perguntas por chunk) e teto de contexto. Entregue **apenas ao ChecklistAgent** via `Supervisor.run`/`graph.run_agents`; demais agentes inalterados.
- Contrato do Checklist preservado: 27 `canonical_key`, estados e persistência (que exige chunk+evidência) intactos. **Sem migration.** Frontend não afetado.
- **Testes:** `pytest -q` = **239 passed** (228 anteriores + 11 novos); sem regressão.
- **E2E 633:** nova análise **V5** (V1–V4 preservadas); dados preservados (analyses 4→5, chunks 1089→1089, evidences 40→73, checklist_results 135→162, llm_runs 20→25). Checklist V5: 27 itens, 3 CONFIRMADO (+1 vs V4: LEILOES_NEGATIVOS_AVERBADOS, com evidência) e 24 PENDENTE (conservador). Risk/Verdict OK. **E2E real da Caixa não declarado concluído.**

**Status global (Task 65):** 🟢 suíte automatizada verde (239 passed); 🟡 E2E real da Caixa em evolução — a matrícula escaneada ainda depende de OCR provisionado no ambiente.

---

## TASK 65.1 — OCR operacional no Docker + telemetria de embeddings do RAG direcionado

- [x] CONCLUÍDA E APROVADA
- Commit: `af00ccb`
- Auditoria: 🟢 aprovada.
- **OCR operacional (local-first, opcional):** `backend/Dockerfile` agora instala as dependências de sistema `tesseract-ocr`, `tesseract-ocr-por` e `poppler-utils`; `backend/requirements.txt` adiciona `pytesseract==0.3.13`, `pdf2image==1.17.0` e `Pillow==11.1.0`. Padrão **`OCR_ENABLED=false`** preservado; `docker-compose.yml` expõe `OCR_ENABLED`/`OCR_LANGUAGE` (defaults `false`/`por`) no serviço backend. OCR continua **opcional** e não substitui o documento original.
- **Validação no container:** `tesseract 5.5.0` com idioma `por` presente, `poppler pdftoppm 25.03.0`, `ocr_available()=True`, imports `pytesseract`/`pdf2image`/`PIL` OK; `ocr_enabled=False` (default) e `ocr_language=por`. Nenhum segredo exposto na verificação.
- **Telemetria de embeddings do RAG direcionado:** `backend/app/rag/checklist_retrieval.py` (`DirectedRetrieval.telemetry`) mede e loga `property_id`, `analysis_id`, itens, embeddings solicitados/executados/falhos, chunks recuperados total e distintos; `backend/app/ai/graph.py` passa `analysis_id`. **Sem multiplicar chamadas de LLM** (5 agentes mantidos) e sem vazar segredos.
- **Matrícula 25278 do imóvel 633 reprocessada com OCR** gerando **nova `document_version` (v2)** e **preservando** original/v1/chunks anteriores: `extraction_quality=OCR`, `ocr=true`, `ocr_engine=tesseract`, `ocr_language=por`, `ocr_pages=2`, `char_count=8355`, 8 chunks. Conteúdo registral real recuperado ("REGISTRO DE IMÓVEIS 7ª Circunscrição Curitiba-Paraná", "Matrícula nº 25.278"). A matrícula não contém averbação de leilão (averbação=0/leilão=0).
- **E2E 633:** nova análise **V6** (V1–V5 preservadas), HTTP 200 em ~61s, 5 agentes `CONCLUIDO` (`gpt-4o-mini`). Telemetria medida: `itens=27`, `embeddings_solicitados=27`, `embeddings_executados=27`, `embeddings_falhos=0`, `chunks_recuperados_total=108`, `chunks_distintos=4`. Preservação: analyses 5→6, document_versions 4→5, document_chunks 1089→1097 (+8 OCR; v1 intacta), evidences 73→108, checklist_executions 6→7, checklist_results 162→189 (+27), llm_runs 25→30 (+5), verdicts 5→6. 27 `canonical_key` intactos. Veredito V6 = INCONCLUSIVO.
- **Checklist V6 conservador (sem forçar confirmação):** 27 PENDENTE / 0 CONFIRMADO. `LEILOES_NEGATIVOS_AVERBADOS` = PENDENTE — correto documentalmente, pois a matrícula não possui averbação de leilão que sustente a confirmação. Nenhuma confirmação artificial foi introduzida.
- **Testes:** 4 novos testes de OCR em `tests/test_document_intelligence.py` (OCR desabilitado mantém comportamento; marcadores de página preservados em PDF multipágina; `run_ocr` usa `por` por padrão; original não é substituído), todos baseados em `monkeypatch` (não exigem Tesseract instalado no ambiente de teste). `pytest -q` = **243 passed** (239 anteriores + 4 novos); sem regressão. Frontend não afetado.
- **Limitação restante (honesta, fora do escopo 65.1):** os chunks de 633 **não possuem embedding** (a geração de embeddings não ocorre na ingestão — lacuna pré-existente da Task 65). Assim, o `HybridRetriever` opera em **modo texto** e as 27 consultas direcionadas recuperam predominantemente chunks genéricos do edital; os chunks OCR da matrícula não são surfaçados no top-k, e por isso o OCR ainda não se reflete em confirmações do Checklist. Corrigir isso é uma mudança de ingestão (geração de embeddings) que **excede o escopo desta task** e deve ser tratada separadamente.

**Status global (Task 65.1):** 🟢 suíte automatizada verde (243 passed); OCR operacional e validado no container; embeddings do RAG direcionado medidos; histórico do 633 preservado (V5→V6). 🟡 O benefício do OCR na análise depende da geração de embeddings na ingestão (limitação registrada, fora do escopo).


---

## TASK 66 — Embeddings na ingestão dos DocumentChunks

- [x] CONCLUÍDA E APROVADA
- Commit: `24e6b2b`
- Auditoria: 🟢 aprovada.
- Objetivo: corrigir a lacuna identificada na TASK 65.1: novos DocumentChunks são criados, mas o pipeline de ingestão não gera/persiste automaticamente o embedding do chunk. Sem isso, o OCR funciona e o RAG direcionado gera embeddings das consultas, porém o pgvector não consegue explorar semanticamente os novos chunks.
- Esta TASK é uma correção de pipeline de ingestão. Não é uma nova arquitetura de RAG e não deve alterar agentes, LangGraph, Checklist, Risk ou Verdict.
- Escopo mínimo: localizar o mecanismo de embeddings existente, reutilizá-lo na ingestão de chunks, persistir o vetor no campo/modelo já existente quando possível e garantir fallback seguro quando não houver API key.
- Não criar novo RAG, novo vector DB, novo agente, novo provider, nova arquitetura, MinIO/Redis/ELK, processamento em massa ou reprocessamento automático de todo o histórico.
- Não apagar documentos, versões, chunks, evidências ou análises existentes.
- Não alterar os 27 canonical keys, estados do Checklist, Risk/Verdict, provider/modelo ou migrations históricas.
- Migração: primeiro verificar o modelo atual. Se o campo vetorial já existir, não criar migration. Só criar migration incremental se houver necessidade real e documentada.
- Fallback obrigatório: sem OPENAI_API_KEY, a ingestão deve continuar funcionando conforme o contrato atual; embedding indisponível não pode quebrar cadastro/upload/análise básica.
- Idempotência: evitar geração duplicada desnecessária para o mesmo DocumentChunk/conteúdo. Reutilizar hash/estado existente quando suportado.
- Testes: validar chunk novo com embedding; ausência de chave; falha de embedding; persistência; rastreabilidade; não duplicação; regressão da ingestão e RAG. Executar pytest -q e comandos frontend somente se afetados.
- E2E controlado 633: não apagar V1–V6. Ingerir uma nova versão controlada da matrícula/documento e confirmar que os novos chunks possuem embedding e podem ser recuperados semanticamente pelo RAG. Depois, se apropriado, executar nova análise e comparar com V6. Não existe meta artificial de confirmações.
- Aceite: pelo menos um chunk novo real do 633 deve ter embedding persistido; uma consulta semântica relacionada deve conseguir recuperar esse chunk; fallback sem chave deve continuar funcionando; suíte verde; histórico preservado.
- Entrega: um único commit, atualização de PROJECT-STATUS.md e PROJECT-HISTORY.md, relatório objetivo de arquivos/testes/E2E, e aguardar auditoria antes da próxima tarefa.
---

## TASK 66 — Execução: embeddings na ingestão dos DocumentChunks

- [x] CONCLUÍDA E APROVADA
- Commit: `24e6b2b`
- Auditoria: 🟢 aprovada.
- **Causa raiz:** `DocumentPipeline.ingest` (`backend/app/documents/pipeline.py`) criava os `DocumentChunk` (conteúdo/página/seção/metadata) mas **nunca** gerava/persistia o embedding. Existiam dois helpers `embed_pending_chunks` (`documents/embedding.py` e `rag/embeddings.py`), porém **nenhum era chamado no pipeline**. Assim todo chunk nascia com `embedding = NULL` e o `HybridRetriever` operava em modo texto.
- **Solução (correção mínima):** `backend/app/documents/embedding.py::embed_pending_chunks` foi reforçado (valida dimensão contra `settings.embedding_dimensions`, é idempotente via `embedding IS NULL`, tolera falha do provider retornando telemetria e nunca levanta) e passou a ser **chamado por `DocumentPipeline.ingest` após o flush dos chunks**, dentro de `try/except` para que falha de embedding **nunca** quebre a ingestão. Reutiliza o gateway/provider existente (`build_gateway().embed`). **Sem migration** (a coluna `document_chunks.embedding = Vector(1536)` já existia). Nenhum RAG/agente/provider novo; LangGraph, Checklist, Risk e Verdict inalterados.
- **Sem API key / falha do provider:** a ingestão continua e os chunks são criados (fallback textual). Sem chave, o helper retorna cedo (não constrói gateway). Falha do provider é registrada com segurança (sem expor chave nem conteúdo) e a ingestão prossegue.
- **Idempotência:** só chunks com `embedding IS NULL` são processados; **sem backfill** automático do histórico.
- **Testes:** novo `tests/test_chunk_embedding.py` (10 testes: chunk novo recebe embedding e é persistido na dimensão correta; múltiplos chunks; sem API key; falha do provider; dimensão incompatível descartada; idempotência; página/versão/metadata preservados após ingestão; falha de embedding não quebra a ingestão; chunk recuperável pelo `HybridRetriever` por similaridade vetorial). Ajustado 1 teste existente (`test_document_embedding_nao_constroi_gateway_sem_api_key`) para o novo contrato de telemetria. `pytest -q` = **253 passed** (243 anteriores + 10 novos); sem regressão. Frontend não afetado.
- **Métricas de embeddings (reingest matrícula 633 v3):** chunks criados=8, embeddings solicitados=8, executados=8, com sucesso=8, com falha=0, chunks com embedding=8, dimensão=**1536**, modelo=`text-embedding-3-small`.
- **Busca semântica (prova):** consulta `"registro de imóveis matrícula 25278 Curitiba consolidação"` → o `HybridRetriever` (com embedding real da consulta) retornou como top-5 **todos os chunks OCR da matrícula v3** (`vector_score` 0,57–0,63 e `text_score = 0,0000`), ou seja, recuperados **puramente por similaridade vetorial** — algo impossível antes da correção. `RAGService`: `vector_search=True`, `text_fallback=False`, 8 chunks.
- **E2E 633 (V6 → V7):** reingestão da matrícula gerou **v3** (`version_id=454`, OCR, 8 chunks, todos vetorizados) preservando v1/v2. Nova análise **V7** (HTTP 200, 5 agentes `CONCLUIDO`, `gpt-4o-mini`, 27.885 tokens) recuperou **exatamente os chunks OCR da matrícula (1752–1759)** — contra os chunks genéricos do edital (276–283) na V6. Checklist V7: **4 CONFIRMADO / 23 PENDENTE** (V6 tinha 0/27); `LEILOES_NEGATIVOS_AVERBADOS` = CONFIRMADO com evidência da matrícula. Melhora **orgânica** (RAG surfaçando o conteúdo OCR), sem forçar confirmação.
- **Contagens antes → depois:** analyses 6→7 (V1–V7 preservadas), document_versions 5→6, document_chunks 1097→1105 (+8), chunks_com_embedding **0→8** (apenas os novos; histórico não sofreu backfill), evidences 108→142, verdicts 6→7. Matrícula: versões [1,2,3] preservadas. 27 `canonical_key` intactos. Backup: `backups/radar-backup-20260924-220845`.
- **Limitação restante (honesta):** apenas os chunks **novos** (ingeridos após a correção) recebem embedding. Os ~1097 chunks históricos do 633 permanecem sem vetor (sem backfill, por escopo). Recuperação semântica plena de documentos antigos exigiria reingestão/backfill controlado — fora do escopo desta task.

**Status global (Task 66):** 🟢 aprovada — suíte reportada 253 passed; embeddings de novos chunks gerados/persistidos na ingestão (1536), idempotentes e tolerantes a ausência de chave/falha; conteúdo OCR da matrícula 633 recuperável semanticamente; histórico V1→V7 preservado. 🟡 Chunks históricos anteriores à correção continuam sem embedding, sem backfill por escopo.

---

## TASK 67 — Validação de qualidade do contexto RAG no E2E real

- [ ] PENDENTE — próxima tarefa operacional do Kiro.

### Objetivo

Agora que a cadeia documental está operacional até a busca vetorial, a próxima etapa é validar exatamente o que cada agente recebe no E2E real do imóvel 633.

A TASK 66 provou que:

- novos chunks recebem embedding;
- pgvector está funcionando;
- busca semântica recupera os chunks OCR da matrícula;
- o E2E V7 passou a recuperar os chunks OCR 1752–1759.

A TASK 67 não deve criar nova arquitetura. Ela deve responder uma pergunta objetiva:

> O retrieval atual está entregando para cada agente o conjunto de evidências/documentos adequado para que a análise do imóvel seja completa, rastreável e conservadora?

### Escopo obrigatório

1. Auditar o retrieval real da V7:
   - identificar os chunks efetivamente entregues a cada um dos 5 agentes;
   - identificar quantos chunks são da matrícula, edital e outras fontes;
   - identificar document_id, document_version_id, página e tipo/origem quando disponíveis;
   - comparar o contexto V6 × V7;
   - não alterar comportamento antes de entender o diagnóstico.

2. Auditar o retrieval direcionado do Checklist:
   - verificar quais chunks foram recuperados por item/pergunta;
   - medir chunks distintos e distribuição por documento;
   - verificar se o teto de contexto está descartando evidências relevantes;
   - verificar se as 27 perguntas estão recebendo contexto suficiente quando há evidência disponível;
   - verificar quantos itens continuam pendentes por ausência real de evidência versus contexto insuficiente, sem inventar respostas.

3. Auditar os 5 agentes separadamente:
   - Documental
   - Jurídico
   - Financeiro
   - Mercado
   - Checklist

   Para cada agente, registrar quais chunks foram usados e se o contexto é coerente com seu domínio.

4. Auditar a origem do contexto:
   - não assumir que todos os agentes devem receber exatamente os mesmos chunks;
   - identificar se a arquitetura atual realmente entrega contexto específico por domínio;
   - identificar se algum agente está recebendo contexto excessivamente genérico;
   - verificar se o OCR da matrícula chega ao Jurídico e Checklist quando necessário;
   - verificar se edital e matrícula podem coexistir no contexto quando uma pergunta depende dos dois.

5. Instrumentação mínima, se necessária:
   - se os logs/telemetria atuais não forem suficientes, adicionar somente a instrumentação necessária para identificar a composição do contexto;
   - registrar IDs, contagens, tipos, versões e páginas;
   - não registrar conteúdo integral dos documentos;
   - não registrar API keys, prompts completos ou dados sensíveis;
   - não alterar o resultado funcional apenas para gerar logs.

6. Teste com o imóvel 633:
   - utilizar V7 como referência existente;
   - não apagar V1–V7;
   - não reingerir documentos sem necessidade;
   - não criar nova análise automaticamente se a instrumentação puder ser feita sem ela;
   - se uma nova análise for necessária para validar a instrumentação, preservar V7 e criar V8 de forma controlada.

### Importante — diagnóstico antes de correção

Não sair alterando o algoritmo de RAG.

Primeiro produzir um diagnóstico objetivo:

- contexto recebido por agente;
- documentos representados;
- chunks representados;
- páginas representadas;
- cobertura por domínio;
- itens do Checklist sem contexto;
- possíveis perdas por limite/deduplicação.

Somente se o diagnóstico comprovar uma falha real de retrieval, implementar a menor correção necessária dentro desta TASK.

### Fora do escopo

Não:

- criar novo agente;
- trocar LLM/provider;
- trocar modelo de embedding;
- criar novo vector database;
- substituir pgvector;
- reescrever o RAG inteiro;
- alterar os 27 canonical keys;
- alterar estados do Checklist;
- alterar Risk Engine;
- alterar Verdict Engine;
- alterar regras de negócio;
- fazer backfill de todos os chunks históricos;
- reprocessar todo o imóvel sem necessidade;
- criar MinIO/Redis/ELK;
- fazer otimização ampla de custo nesta etapa;
- apagar histórico V1–V7;
- alterar migrations históricas.

### Testes

Adicionar somente testes necessários para o diagnóstico/instrumentação ou para uma correção comprovada.

Obrigatório executar:

pytest -q

Se backend não for alterado funcionalmente, não criar testes artificiais apenas para aumentar contagem.

Frontend só deve ser testado se for afetado.

### Critérios de aceite

A TASK 67 somente será considerada concluída quando houver:

1. diagnóstico real dos chunks/contextos entregues aos 5 agentes;
2. comparação V6 × V7 do contexto recuperado;
3. diagnóstico do retrieval direcionado das 27 perguntas do Checklist;
4. identificação clara de quais documentos/versões/páginas estão representados;
5. confirmação de que o chunk OCR da matrícula pode chegar aos agentes que precisam dele;
6. identificação de eventuais gargalos de contexto, deduplicação ou limite;
7. nenhuma confirmação artificial introduzida;
8. suíte verde;
9. histórico V1–V7 preservado;
10. se houver correção, ela deve ser mínima, testada e justificada pelo diagnóstico.

### Entrega

Criar um único commit somente se houver alteração de código/documentação necessária.

Atualizar:

- docs/PROJECT-STATUS.md
- docs/PROJECT-HISTORY.md

Informar:

- diagnóstico por agente;
- chunks/documentos/páginas recuperados;
- comparação V6 × V7;
- Checklist: cobertura por item/grupo;
- testes;
- se houve alteração funcional;
- limitações restantes.

Se a investigação concluir que o código já está adequado e somente documentação/telemetria foi necessária, registrar isso claramente.

**Depois do commit, PARAR e aguardar auditoria. Não iniciar TASK 68.**

---

## TASK 67 — Execução: diagnóstico da qualidade do contexto RAG (E2E 633, V7)

- [x] CONCLUÍDA (aguardando auditoria) — **diagnóstico concluído sem necessidade de alteração funcional** (a menor correção necessária está fora do escopo desta task; ver conclusão).

### Diagnóstico por agente (dados reais de `llm_runs.retrieved_chunk_ids`)

Referência: análises do 633 — V6 = `analysis_id` 229, V7 = `analysis_id` 266.

```text
V7 (analysis_id=266) — TODOS os 5 agentes receberam os MESMOS 8 chunks:
  Documental : 8 chunks  -> MATRICULA v3 (doc 192)  [1752..1759]   edital: 0
  Jurídico   : 8 chunks  -> MATRICULA v3 (doc 192)  [1752..1759]   edital: 0
  Financeiro : 8 chunks  -> MATRICULA v3 (doc 192)  [1752..1759]   edital: 0
  Mercado    : 8 chunks  -> MATRICULA v3 (doc 192)  [1752..1759]   edital: 0
  Checklist  : 8 chunks  -> MATRICULA v3 (doc 192)  [1752..1759]   edital: 0
```

### Comparação V6 × V7

```text
V6 (analysis_id=229):
  4 agentes genéricos: 8 chunks = 1 MATRICULA v1 (276) + 7 EDITAL v1 (277..283)
  Checklist          : 4 chunks = 1 MATRICULA v1 + 3 EDITAL v1
  -> edital-dominado; matrícula quase ausente.

V7 (analysis_id=266):
  5 agentes: 8 chunks = 8 MATRICULA v3 (1752..1759); EDITAL = 0
  -> matrícula-only; edital totalmente AUSENTE.
```

Ou seja: a V7 corrigiu a ausência da matrícula, mas passou ao extremo oposto — **edital e matrícula não coexistem** no contexto. O OCR da matrícula chega ao Jurídico/Checklist (bom), mas o edital deixou de chegar a qualquer agente.

### Cobertura das 27 perguntas do Checklist (V7, execução 1089)

- **4 CONFIRMADO** (todos com evidência da matrícula v3): `CONSOLIDACAO_REGISTRADA` (1752), `LEILOES_NEGATIVOS_AVERBADOS` (1756), `VAGA_MATRICULA` (1752), `PENHORA_INDISPONIBILIDADE` (1754).
- **2 PENDENTE com evidência da matrícula** (agente conservador — Caso C): `ACAO_QUESTIONAMENTO` (1756), `QUITACAO_80` (1758).
- **21 PENDENTE sem evidência**, classificados:
  - **Caso A — ausência documental / dependem de engine determinístico ou comparáveis (PENDENTE correto):** Mercado (`COMPARAVEIS_SUFFICIENTES`, `CONDOMINIO_PORTARIA`, `ILIQUIDEZ`, `REFORMA_LIQUIDEZ`, `REGIAO_SERVICOS`), `DISTANCIA_USUARIO`, Financeiro `RETORNO_SELIC`/`PRAZO_DOIS_ANOS`/`REFORMA_GRANDE`, Desocupação (`ETICA_OCUPACAO`/`LOCACAO_REGISTRADA`/`TERCEIRO_OCUPANTE`), Jurídico `EVICCAO`/`GARANTIA_DIVIDA_TERCEIRO`.
  - **Caso B — falha de retrieval (a informação existe no edital, mas o edital não chegou ao contexto):** `EDITAL_LIDO`, Financeiro `RESPONSABILIDADE_DEBITOS`/`CONDOMINIO_ALTO`, Jurídico `INTIMACAO_EDITAL`/`NOTIFICACAO_DOIS_LEILOES`/`LANCE_MENOR_50_AVALIACAO`/`INTIMACAO_PESSOAL`.

### Causa raiz (comprovada por instrumentação e probes ao vivo)

- No imóvel 633, **apenas** os 8 chunks da matrícula v3 possuem embedding; o edital (doc 193 e 195, 544 chunks cada) e a matrícula v1/v2 têm **0 embedding** (consequência do escopo da Task 66: sem backfill do histórico).
- O ranking híbrido é `final = vetor·0,7 + texto_norm·0,3`. Com embedding, os chunks da matrícula pontuam ~0,35; o melhor edital por texto puro pontua ~0,30. Assim a matrícula **ganha todos os 8 slots**, em qualquer consulta.
- Probes: a query genérica do fluxo (`"análise documental do imóvel"`) com embedding retorna 8 matrícula e 0 edital; sem embedding retorna 0 (não casa o texto do edital). Nas 27 consultas por item do Checklist, **100% dos candidatos são matrícula (108/108), 0 edital** — mesmo em modo texto, porque `build_item_query` gera frases longas e `plainto_tsquery` exige todos os termos (AND), e `expected_evidence`/`related_rules` estão vazios para os itens de edital.
- O edital **é** recuperável por texto com termos curtos (`avaliação` ts_rank 0,3; `débitos` 0,2; `comissão leiloeiro` 0,11), mas as consultas atuais não usam esse formato.

Conclusão: **não é perda por limite** (`PER_ITEM_LIMIT=4`, `MAX_TOTAL_CHUNKS=24`) **nem por deduplicação**; é assimetria de cobertura de embedding (só a matrícula está vetorizada) combinada com um ranking que não garante diversidade por documento e com consultas que não alcançam o edital por texto.

### Alterações

**Diagnóstico concluído sem necessidade de alteração funcional.** Justificativa objetiva: a menor correção que realmente faria edital e matrícula coexistirem exige uma das opções abaixo, **todas fora do escopo declarado da TASK 67**:

1. gerar embedding do edital (backfill dos ~1097 chunks históricos) — proibido;
2. reescrever a semântica de consulta/casamento textual (ex.: `websearch_to_tsquery`, extração de palavras-chave, `OR`) — caracteriza reescrever o RAG, proibido;
3. cota de diversidade por documento no `retrieve_for_checklist` — **não resolve**, pois o edital sequer entra como candidato (0/108).

Assim, seguindo a regra da própria task (“se o código já estiver adequado, não inventar alteração funcional”; “somente implementar a menor correção se ela existir e for mínima”), **nenhum código foi alterado**. A instrumentação atual (`llm_runs.retrieved_chunk_ids` por agente + telemetria do `checklist_retrieval`) já é suficiente para responder “quais evidências chegaram a cada agente”, portanto **nenhuma instrumentação adicional foi necessária**.

### Recomendação para a próxima task (fora do escopo da 67)

Tornar edital e matrícula recuperáveis em conjunto, por uma destas vias mínimas (a decidir em task própria): (a) gerar embedding do edital via reingestão controlada (equivalente à Task 66 aplicada ao edital, sem backfill em massa); ou (b) garantir cobertura por documento no retrieval (cota/round-robin por `document_id`) **em conjunto** com consultas por texto que alcancem o edital. Sem isso, itens do Checklist que dependem do edital permanecerão PENDENTE por falha de retrieval, não por ausência documental.

### Preservação e testes

- **V1–V7 preservadas**; nenhum dado histórico alterado; nenhuma confirmação artificial. Não foi criada V8 (o diagnóstico foi possível com os dados/telemetria já persistidos).
- `pytest -q` = **253 passed** (baseline intacto; nenhum código alterado nesta task).

**Status global (Task 67):** 🟢 diagnóstico concluído e documentado; instrumentação suficiente; sem alteração funcional (correção necessária fora do escopo). 🔴 Falha de retrieval real registrada: na V7 o edital não coexiste com a matrícula no contexto dos agentes — recomendada correção mínima em task seguinte.
## TASK 68 — Recuperação conjunta de edital + matrícula no E2E real

**Status:** PENDENTE — próxima tarefa operacional do Kiro.

### Objetivo

Corrigir a falha de retrieval comprovada na TASK 67, fazendo com que o contexto do imóvel 633 consiga representar edital e matrícula simultaneamente quando ambos forem relevantes, sem reescrever o RAG e sem alterar as regras de negócio.

A TASK 68 é a última correção funcional planejada antes da validação final do MVP, salvo surgimento de uma regressão objetiva durante a execução.

### Contexto e causa raiz já comprovada

A TASK 67 foi aprovada em auditoria.

No E2E V7 do imóvel 633:
- os 5 agentes receberam 8 chunks cada;
- os 8 eram exclusivamente da matrícula v3, chunks 1752–1759;
- o edital não apareceu em nenhum contexto;
- 108/108 candidatos das 27 consultas direcionadas do Checklist eram matrícula e 0 edital;
- o problema não foi causado por PER_ITEM_LIMIT, MAX_TOTAL_CHUNKS ou deduplicação;
- a causa foi a assimetria de embeddings: a matrícula v3 tem 8 embeddings, enquanto os chunks históricos do edital permanecem sem embedding;
- o ranking híbrido atual usa aproximadamente 70% vetor + 30% texto, permitindo que a matrícula vetorizada ocupe os slots antes dos candidatos textuais do edital;
- o edital é recuperável por texto com termos curtos, mas as consultas atuais não o alcançam de forma suficiente.

### Estratégia obrigatória

A correção deve ser mínima, controlada e baseada no mecanismo já existente.

1. Não criar novo mecanismo de embeddings.
2. Reutilizar o pipeline de ingestão existente da TASK 66.
3. Reprocessar somente os documentos necessários do imóvel 633, principalmente o edital usado no E2E.
4. Não fazer backfill global do banco.
5. Não apagar versões anteriores.
6. Não apagar V1–V7.
7. Não alterar pesos globais do ranking sem evidência objetiva de que isso é indispensável.
8. Não reescrever o RAG.
9. Não alterar os 27 canonical keys, estados ou regras do Checklist.
10. Não alterar Risk Engine ou Verdict Engine.
11. Não criar novos agentes, providers, vector DB ou infraestrutura.

### Passo 1 — Identificar exatamente os documentos do edital do 633

Antes de ingerir:
- confirmar quais document_id/document_version_id correspondem ao edital usado no V7;
- confirmar nome, tipo, versão, hash/origem e quantidade de chunks;
- confirmar que o documento correto é o edital do imóvel 633;
- não assumir IDs sem consultar o banco.

### Passo 2 — Reingestão controlada do edital

Usar o DocumentPipeline.ingest já existente, com a configuração normal de produção local.

Objetivo:
edital original → normalização/OCR se necessário → chunks → embeddings → pgvector

Validar:
- nova document_version criada somente para o documento reprocessado;
- chunks novos criados;
- embeddings persistidos nos novos chunks;
- dimensão correta conforme configuração;
- páginas/seções/metadata preservados;
- hash/original/source preservados;
- versão anterior intacta;
- nenhum outro documento histórico reprocessado.

Se houver mais de um arquivo que represente o edital no imóvel 633, escolher apenas os necessários para o E2E e documentar a decisão. Não fazer reprocessamento em massa.

### Passo 3 — Prova isolada do retrieval

Antes de executar o E2E completo, executar consultas controladas que comprovem:
- consulta jurídica relacionada a intimação/notificação;
- consulta financeira relacionada a débitos/IPTU/condomínio;
- consulta relacionada ao valor do segundo leilão/avaliação;
- consulta documental relacionada ao edital;
- consulta relacionada à matrícula, para garantir que a correção não expulsou a matrícula.

Verificar se os resultados passam a incluir chunks do edital e se a matrícula continua recuperável.

O objetivo é comprovar coexistência, não maximizar número de chunks.

### Passo 4 — E2E controlado

Executar nova análise do imóvel 633 somente depois da prova isolada.

A nova análise será a próxima versão após V7, preservando V1–V7.

Registrar:
- novo analysis_id/versão;
- chunks recuperados por agente;
- quantidade de chunks por documento;
- matrícula x edital;
- páginas e versões;
- resultado dos 5 agentes;
- tokens/custo reportados;
- Checklist 27 itens;
- evidências geradas;
- Risk/Verdict;
- ausência de confirmações artificiais.

### Passo 5 — Validar especificamente os 7 itens afetados

Verificar individualmente:
- EDITAL_LIDO
- RESPONSABILIDADE_DEBITOS
- CONDOMINIO_ALTO
- INTIMACAO_EDITAL
- NOTIFICACAO_DOIS_LEILOES
- LANCE_MENOR_50_AVALIACAO
- INTIMACAO_PESSOAL

Para cada item, registrar se:
- recebeu contexto suficiente;
- recebeu evidência do edital;
- permaneceu PENDENTE por ausência real de informação;
- mudou de estado somente quando houver evidência documental suficiente.

Não existe meta de quantidade de CONFIRMADO. O objetivo é eliminar a ausência artificial do edital do contexto.

### Passo 6 — Validar Checklist e conservadorismo

Não considerar sucesso apenas porque o edital apareceu.

Verificar:
- nenhuma confirmação baseada apenas na presença do documento;
- respostas continuam dependentes de evidência;
- evidências apontam para documento/version/chunk/página corretos;
- itens sem informação continuam PENDENTE;
- não houve alteração dos 27 canonical keys;
- não houve mudança artificial no Risk/Verdict.

### Correção adicional de retrieval

Somente se, após os embeddings do edital, o retrieval ainda excluir sistematicamente o edital, diagnosticar o menor ajuste possível.

Qualquer ajuste adicional deve ser pequeno, justificado por dados do E2E, coberto por testes e limitado ao problema de coexistência edital + matrícula.

Não alterar pesos globais ou semântica das consultas por tentativa e erro.

Se os embeddings do edital forem suficientes para resolver o problema, não alterar o algoritmo de retrieval.

### Testes obrigatórios

Executar:
pytest -q

Se houver alteração funcional no retrieval, adicionar somente os testes necessários para proteger a correção.

Não criar testes artificiais apenas para aumentar a contagem.

### Fora do escopo

Não:
- fazer backfill global;
- reprocessar todos os documentos do imóvel;
- apagar V1–V7;
- criar versões extras sem necessidade operacional;
- trocar LLM/provider/modelo de embedding;
- criar novo agente;
- trocar pgvector/vector DB;
- reescrever RAG;
- alterar os 27 canonical keys;
- alterar estados do Checklist;
- alterar regras de negócio;
- alterar Risk/Verdict sem evidência de regressão;
- criar MinIO/Redis/ELK;
- fazer otimização ampla de custo;
- fazer refatoração arquitetural.

### Critérios de aceite

1. edital correto do imóvel 633 reprocessado controladamente com chunks embeddados;
2. versão anterior preservada;
3. consultas isoladas recuperam evidência do edital;
4. matrícula continua recuperável;
5. edital e matrícula coexistem no contexto quando necessários;
6. os 5 agentes executam com sucesso;
7. os 7 itens afetados são auditados individualmente;
8. nenhuma confirmação artificial é introduzida;
9. Checklist continua com 27 canonical keys e estados válidos;
10. Risk/Verdict continuam rastreáveis;
11. pytest -q passa sem regressão;
12. V1–V7 permanecem preservadas;
13. nenhuma alteração fora do escopo é introduzida;
14. documentação registra exatamente o que foi reprocessado, quantos embeddings foram criados e o resultado do E2E.

### Entrega

Um único commit de implementação/documentação.

Atualizar:
- docs/PROJECT-STATUS.md
- docs/PROJECT-HISTORY.md

Informar:
- documentos/version IDs reprocessados;
- chunks antes/depois;
- embeddings antes/depois;
- provas isoladas de retrieval;
- comparação V7 × nova análise;
- distribuição edital/matrícula por agente;
- Checklist dos 27 itens, com foco nos 7 afetados;
- testes;
- tokens/custo do E2E;
- limitações restantes.

**Depois do commit, PARAR e aguardar auditoria. Não iniciar TASK 69.**

### Regra de encerramento

Se a TASK 68 passar na auditoria e o E2E final estiver íntegro, o próximo passo não será criar novas funcionalidades: será a revisão final da SPEC, fechamento da documentação e declaração do MVP como concluído, registrando como backlog apenas melhorias futuras que não sejam necessárias para o fluxo principal.

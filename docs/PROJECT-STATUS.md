# Radar Leilão — Controle Central do Projeto

> Documento operacional central do desenvolvimento.  
> Última consolidação: 24/09/2026  
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

**Último commit de implementação:** `6d91485a1188c0f2cb178f0b6ddb9b3ab769edaa`  
**Último commit de documentação:** `538f387ce5929e6cbbcb1c7bcf7d2ed790515863`  
**Mensagem:** `chore: operacao local segura com rebuild, logs e protecao de dados`

**Última TASK aprovada:** TASK 64

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

**Status global:** 🟡 MVP em construção — base operacional validada; próxima etapa é corrigir a cobertura documental/RAG antes do E2E final.

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

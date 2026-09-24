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


## TASK 64 — Operação segura local: rebuild, .env, logs e proteção de dados

**Status:** 🟡 PENDENTE — próxima task do Kiro.

### Objetivo

Corrigir o ciclo operacional local antes da nova validação E2E com LLM real. O ambiente precisa:

- usar o .env real como fonte de configuração;
- reconstruir backend/frontend quando código ou Dockerfile mudar, evitando imagem antiga;
- preservar integralmente os volumes existentes do PostgreSQL e documentos;
- ter logs consultáveis e salváveis para investigação;
- documentar os comandos operacionais no WSL;
- manter migrations seguras para banco existente com dados.

### Escopo obrigatório

1. **Scripts oficiais**
   - revisar scripts/start.sh, scripts/restart.sh e scripts/setup.sh;
   - garantir que o fluxo de atualização reconstrua backend/frontend quando necessário;
   - não usar down -v nos fluxos normais;
   - manter stop.sh/restart.sh preservando volumes;
   - criar scripts/logs.sh com comandos status, tail, follow e save;
   - save deve gerar snapshots em logs/ com timestamp;
   - mensagens dos scripts devem deixar explícito quando uma operação preserva dados.

2. **Docker Compose**
   - revisar a estratégia de build/recreate do backend e frontend;
   - manter postgres_data e backend_storage como volumes persistentes;
   - adicionar rotação de logs do Docker por serviço, sem criar dependência externa de observabilidade;
   - não introduzir MinIO, Redis ou outro serviço sem necessidade;
   - não alterar portas/contratos existentes sem justificativa.

3. **Logs da aplicação**
   - garantir logs suficientemente detalhados do backend para investigar falhas de upload, documentos, RAG, agentes, LLM, migrations e endpoints;
   - logs devem conter timestamp e contexto útil, mas nunca imprimir OPENAI_API_KEY ou outros segredos;
   - manter docker compose logs funcionando;
   - não registrar conteúdo sensível de documentos desnecessariamente.

4. **Proteção do banco**
   - não apagar, recriar ou resetar o banco existente;
   - não executar docker compose down -v;
   - não alterar migrations já aplicadas para corrigir banco existente;
   - se uma alteração de schema for necessária, criar nova migration Alembic incremental;
   - qualquer DDL deve preservar os dados existentes e ser validado em banco com dados;
   - validar também alembic upgrade head em banco limpo;
   - não alterar dados existentes manualmente.

5. **.env / LLM**
   - .env.example permanece sem segredo real;
   - documentação deixa claro que Compose lê .env, não .env.example;
   - não exibir chave em logs, testes ou mensagens de erro;
   - após mudança do .env, restart.sh deve aplicar a configuração ao container.

6. **Testes e validação**
   - docker compose config;
   - docker compose up -d --build ou equivalente seguro;
   - ./scripts/health.sh;
   - confirmar containers backend/frontend foram realmente recriados com a imagem atual;
   - confirmar alembic_version sem regressão;
   - pytest -q e testes frontend relevantes;
   - validar logs.sh status, tail, follow (interrompível) e save;
   - confirmar que os dados existentes permanecem após stop/restart/rebuild.

### Fora do escopo

- não mudar LangGraph, agentes, RAG, Risk, Verdict ou Checklist;
- não trocar modelo LLM;
- não refatorar o domínio;
- não criar nova infraestrutura externa de logs;
- não fazer reset de banco;
- não alterar dados existentes manualmente.

### Critério de aceite

A task só será concluída se for possível executar no WSL:

    ./scripts/backup.sh
    ./scripts/restart.sh
    ./scripts/health.sh
    ./scripts/logs.sh status
    ./scripts/logs.sh tail
    ./scripts/logs.sh save

sem perda de dados, com backend/frontend usando a versão atual do código, migrations consistentes e logs recuperáveis.

### Documentação de apoio

- docs/OPERATIONS.md
- docs/LOCAL-SETUP.md

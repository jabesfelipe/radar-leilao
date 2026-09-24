# Radar Leilão — Histórico de Implementação

Este documento registra a trajetória técnica do projeto e os commits que representam as etapas já executadas.

## Marco inicial

- `5e2872cb790299122697774931696f9b1266eadd` — docs: init
- `3f370691fb3f20d90e950ca18d293ad66afb6bf8` — docs: adiciona spec oficial do vibe coding do MVP
- `1333c2f43277c2c6be3e6aad3ca0247ade19af15` — docs: consolida arquitetura mestre completa para vibe coding
- `baebc3eb1f6ec297cabb2437786aa63d0ccf6d55` — docs: remove documentos antigos consolidados na arquitetura mestre

## Implementação do MVP

Os marcos de implementação anteriores permanecem registrados neste histórico.

## Correções que devem permanecer registradas

### Reanálise incremental
`d416345516fe11c7c27a1684a4071d916433dfaf` — correção para executar Checklist apenas quando efetivamente afetado.

### Risk Engine
`acc515f321a6f827ae32c10be98972940530fe08` — remoção de regras de risco não formalizadas.

### Cadastro de imóvel
`d244a08e375e4b2c23f88e9acbeccd84fe12719b` — remoção de enum artificial de tipo de imóvel.

## TASK 44 — Mercado + Ocupação
- `13b6c9325978908b7960e17edb65700fd94c0aa2` — feat: implementa mercado e ocupacao no hub do imovel
- Auditoria: 🟢 aprovado.

## TASK 45 — Checklist no Hub
- `a8fe36ac643090ff4c74008dfe4bb3c2f9aaf0d2` — feat: implementa checklist no hub do imovel
- `14da0329cb7c03fd59291d6b0fc585943fc83abc4` — fix: corrige contrato e valores ausentes do checklist
- Auditoria: 🟢 aprovado.

## TASK 46 — Riscos + Veredito no Hub
- `3480a5ce388d5ff45250c217dcdb394f7f583c1d` — feat: implementa riscos e veredito no hub do imovel
- Auditoria: 🟢 aprovado.

## TASK 47 — Histórico no Hub
- `bed0c5688497accbd4db8413e40077c3cef9232d` — feat: implementa historico no hub do imovel
- `b08b63002e7365e55be9b99d2abd6057e473332d` — fix: ajusta contrato do historico no hub do imovel
- Auditoria final: 🟢 aprovado.

## TASK 49 — Revisão da integração Frontend ↔ Backend
- `2a549c8e9b90e6fc07e50b1f915f109fdc31ca02` — fix: revisa integracao frontend backend
- Auditoria: 🟢 aprovado.

## TASK 50 — Testes de integração
- `1e50f30e09f314e058eaa396a49b0a769209f6c2` — test: adiciona testes de integracao do radar
- Auditoria: 🟢 aprovado.

## TASK 51 — Primeiro E2E com imóvel real da Caixa
- `ea7db957b6ef6e739bfa19d086b4a508d462acc6` — test: executa primeiro e2e com imovel real da caixa
- Auditoria: 🟡 não aprovado como E2E completo.

## TASK 52 — Cadeia de migrations validada
- `b676a889fdfb79c4609b72107a345f9b5ed3a080` — fix: corrige cadeia de migrations do radar
- Migrations 0001 → 0008 concluídas em banco limpo; 211 passed, 10 failed por problemas de aplicação fora do escopo.

## TASK 53 — Snapshot anterior do Checklist
- `f36cecebb490112945d2f6a91ae96bf2e9492157` — fix: corrige snapshot anterior do checklist
- Auditoria: 🟢 aprovado.

## TASK 54 — Correção da próxima falha
- `ecde86518d4d9d4136184877974f103b9735e80d` — fix: corrige proxima falha da suite
- Auditoria: 🟢 aprovado.
- Suíte: 213 passed, 8 failed.

## TASK 55 — Correção da próxima falha
- `27a65e3cd21053d710c68338a4f1a853a4ad8caa` — fix: corrige proxima falha da suite
- Auditoria: 🟢 aprovado.
- Suíte: 214 passed, 7 failed.

## TASK 56 — Correção da próxima falha
- `1aa3912445c3e25a6f0b9e2ac4fa93d9e82f1d74` — fix: corrige proxima falha da suite
- Auditoria: 🟢 aprovado.
- Suíte: 215 passed, 6 failed.

## TASK 57 — Correção da próxima falha
- `4c26ee67243cc622b89748a607fc01e3e294ca26` — fix: corrige proxima falha da suite
- Auditoria: 🟢 aprovado.
- Corrigida fixture de `test_extraction.py` para fornecer `success=True`.
- Suíte: 216 passed, 5 failed.

## TASK 58 — Correção da próxima falha de integração
- `23b47172f1855e7f6facde86142ed7762759615c` — fix: corrige serializacao decimal na integracao
- Auditoria: 🟢 aprovado.
- A falha foi reproduzida e a causa real confirmada: o PATCH do Checklist retornava `{}` porque o ORM era retornado após `db.commit()` sem `db.refresh(result)`.
- Correção mínima: `db.refresh(result)` em `main.py`.
- Contrato preservado; nenhum schema, migration, teste ou regra de negócio alterado.
- Resultado: teste alvo passou; `test_integration_flows.py`: 12 passed, 4 failed; suíte: 217 passed, 4 failed.

## TASK 59 — Correção da primeira falha do fluxo de análise
- `92c3e44aa314fc38c402a895d64b9add17381d85` — fix: corrige primeira falha do fluxo de analise
- Auditoria: 🟢 aprovado.
- Correção: serialização do resultado financeiro antes da criação do veredito.

## TASK 60 — Correção das 3 falhas restantes da integração
- `1262637fa681d056f4191a8e15cbb72aefcc4038` — fix: corrige 3 falhas restantes da integracao
- Auditoria: 🟢 aprovado por inspeção do diff.
- `get_property` passou a ordenar as análises por versão.
- `create_analysis` passou a consultar a maior versão persistida diretamente no banco, evitando duplicidade na reanálise incremental.
- Sem migration/schema, alteração de testes ou nova regra de negócio.
- CI/workflow não publicou execução para este commit; não há contagem independente de testes.


---

## Consolidação de validação — 21/09/2026

### Validação da TASK 60 em runtime

Após as correções da TASK 60, os três testes diretamente relacionados à correção passaram:

```text
3 passed, 13 deselected
```

Em seguida, a suíte completa de integração foi executada:

```text
pytest -q tests/test_integration_flows.py
16 passed, 2110 warnings in 3.29s
```

### Validação da suíte completa

```text
pytest -q
221 passed, 2744 warnings in 9.41s
```

Resultado: **221 testes passaram e nenhuma falha automatizada permanece neste estado do projeto.**

Os warnings foram registrados para acompanhamento futuro, mas não bloquearam a validação.

### Documentação mestre

A especificação principal foi movida da raiz para:

`docs/SPEC-VIBE-CODING-RADAR-LEILAO.md`

Na consolidação, a referência residual a **Java 21 / Spring** na arquitetura foi corrigida para **Python + FastAPI**, alinhando a documentação com a implementação efetiva.

### Estado após a consolidação

O projeto entra na fase de validação operacional com imóveis reais. A suíte automatizada está verde, mas o E2E real com documentos da Caixa, OCR e LLM continua sendo uma etapa distinta e deve ser validado antes de declarar o fluxo real completamente concluído.


## TASK 61 — Setup local automatizado (WSL2 + Docker)

- Objetivo: permitir subir o Radar Leilão em um notebook novo (Windows + WSL2 + Docker) sem configuração manual de banco/migrations/infra.
- Implementação:
  - `docker-compose.yml`: serviços `postgres` (pgvector/pgvector:pg16), `backend` (FastAPI) e `frontend` (React/Vite). Volumes persistentes `postgres_data` e `backend_storage`. Healthchecks em postgres e backend. Portas e credenciais via `.env` (com defaults).
  - `backend/Dockerfile` + `docker/backend-entrypoint.sh`: espera o PostgreSQL, executa `alembic upgrade head` (mecanismo oficial, sem estratégia paralela) e sobe o Uvicorn.
  - `frontend/Dockerfile`: build com `VITE_API_URL` embutido e serve via `vite preview` na porta 5173.
  - `.env.example` revisado com todas as variáveis realmente usadas (PostgreSQL, backend, frontend, LLM). `.env` continua ignorado pelo `.gitignore`.
  - Scripts em `scripts/`: `setup.sh`, `start.sh`, `stop.sh`, `restart.sh`, `health.sh`, `reset.sh` (destrutivo, com confirmação), `backup.sh`, `restore.sh`.
  - `docs/LOCAL-SETUP.md`: passo a passo para usuário leigo (WSL2, Docker, clone, `.env`, setup, URLs, parar/iniciar, health, reset, backup/restore) + troubleshooting.
- Decisões:
  - **MinIO não incluído**: o código atual armazena documentos no filesystem local (`storage/documents`), sem MinIO/S3. Persistência garantida por volume Docker (`backend_storage`). Documentado em `docs/LOCAL-SETUP.md`.
  - **Redis não incluído**: não há dependência real no código.
  - **LLM opcional**: a stack sobe sem `OPENAI_API_KEY`; apenas as etapas de IA ficam indisponíveis, sem quebrar o sistema.
- Validação real (WSL2 → Docker):
  - `docker compose config` válido; `docker compose up -d --build` subiu os 3 serviços.
  - Backend `healthy`; `/health` = `{status: ok}`; Swagger `/docs` = HTTP 200; frontend `:5173` = HTTP 200.
  - Migrations aplicadas automaticamente no boot: `alembic_version = 0008_extracao_documental`.
  - `scripts/health.sh`: PostgreSQL/pgvector/Migrations/Backend/Frontend = OK (5/0).
  - `pytest -q` = **221 passed** (sem regressão; nenhum teste removido; nenhuma regra de negócio alterada).
- Limitações conhecidas:
  - Primeiro `setup.sh`/build é demorado (instala dependências pesadas do backend e faz build do frontend).
  - Backup cobre banco (pg_dump) + storage de documentos; não cobre `.env`, imagens Docker nem código-fonte.
  - `reset.sh` é destrutivo (remove volumes) e exige confirmação; não faz parte do fluxo normal.


## TASK 62 — Cadastro completo do imóvel de leilão (entrada no fluxo do Radar)
- Objetivo: transformar o cadastro (antes só 5 campos) em um fluxo guiado compatível com o domínio, conectando a entrada do imóvel ao fluxo de análise já existente. Sem recriar IA, RAG, LangGraph, agentes, Risk/Verdict/Checklist/Finance Engine ou criar fluxo paralelo de análise.

### Novo fluxo de cadastro
```
Novo imóvel
   → 1. Dados básicos (identificação, físicos, identificação na origem)
   → 2. Dados do leilão (avaliação, 1º/2º leilão, leiloeiro, edital, matrícula)
   → 3. Fontes oficiais (página do imóvel, edital, matrícula, outras)
   → 4. Documentos (upload; não bloqueia o cadastro)
   → 5. Revisão
   → Cadastrar imóvel (transacional)
   → Dossiê do imóvel (abre automaticamente)
   → Executar análise completa (fluxo existente)
   → Documento → Jurídico → Financeiro → Mercado → Checklist → Consolidação
   → Risk Engine → Verdict Engine → Histórico
```

### Backend (reutiliza os modelos existentes; nenhum modelo duplicado)
- `backend/app/models.py`:
  - `Property` ganhou: `neighborhood`, `private_area_m2`, `parking_spots`, `description` (descrição original preservada), e identificação na origem `origin`, `origin_property_code`, `inscription`, `modality`, `system` (extensíveis, sem enum rígido).
  - `Auction` ganhou 1º/2º leilão preservados separadamente: `first_auction_date/value`, `second_auction_date/value` (não sobrescrevem `appraisal_value`/`bid_value`).
  - `AuctionNotice` ganhou `item` (item do edital).
  - Novo modelo `PropertySource` (tabela `property_sources`): `source_type`, `url`, `description`, `origin` — múltiplas fontes por imóvel, rastreáveis.
- `backend/migrations/versions/0009_cadastro_completo_imovel.py` (down_revision `0008_extracao_documental`): adiciona as colunas acima e cria `property_sources`. Migrations antigas não foram alteradas.
- `backend/app/schemas.py`: `PropertyCreate`/`PropertyOut` estendidos; `AuctionCreate`/`AuctionNoticeCreate` estendidos; novos `PropertySourceCreate/Out`, `AuctionFull`, `AuctionNoticeFull`, `RegistrationFull` e o schema composto `PropertyFullCreate`.
- `backend/app/main.py`:
  - Novo `POST /api/imoveis/completo` — cadastro **transacional** (um único commit): Property + Auction + AuctionNotice + PropertyRegistration + PropertySource, com eventos e histórico. Se qualquer etapa falhar, nada é persistido. Documentos e análise LLM ficam de fora (etapas próprias).
  - Novos `GET`/`POST /api/imoveis/{id}/fontes`.
  - `get_property` agora também retorna `edital`, `matricula` e `fontes`.
  - `POST /api/imoveis` (cadastro simples) mantido intacto para não quebrar contratos existentes.

### Frontend (reutiliza o design system; sem react-router — navegação manual existente)
- `frontend/src/pages/PropertyWizard.tsx` (novo): wizard de 5 etapas com stepper, reutilizando `Card`/`Section`/`Input`/`Select`/`Textarea`/`Button` e as classes `.dossier-form`. Valida obrigatórios (nome, cidade, UF, tipo), números e URLs. Envia `POST /api/imoveis/completo`, faz upload dos documentos (best-effort, não bloqueia) e navega direto ao Dossiê.
- `frontend/src/pages/PropertiesPage.tsx`: passa a usar o wizard; após salvar, abre o Dossiê do imóvel criado.
- `frontend/src/services/properties.ts`: novos tipos e `createPropertyFull`, `getPropertyDetail`, `listSources`.
- `frontend/src/pages/PropertyDetailPage.tsx`: Visão geral enriquecida (avaliação, 2º leilão, matrícula, edital, origem, descrição original) e seção **Leilão** agora real (dados do leilão + edital + item + fontes com links) — antes era placeholder.
- `frontend/src/styles.css`: classes `wizard-*` e `detail-sources`/`detail-description`.

### Mapeamento Tela → API → Tabela (principais dados)
| Tela (wizard) | API | Tabela.coluna |
| --- | --- | --- |
| Nome, cidade, UF, tipo, bairro, áreas, quartos, vagas, descrição | POST /api/imoveis/completo (`imovel`) | `properties.*` |
| Origem, nº imóvel, inscrição, modalidade, sistema | idem (`imovel`) | `properties.origin/origin_property_code/inscription/modality/system` |
| Avaliação, 1º/2º leilão, leiloeiro | idem (`leilao`) | `auctions.appraisal_value/first_*/second_*/auctioneer` |
| Nº do edital, item | idem (`edital`) | `auction_notices.identifier/item` |
| Matrícula, ofício, comarca | idem (`matricula`) | `property_registrations.*` |
| Fontes (tipo/URL/descrição) | idem (`fontes`) / POST /api/imoveis/{id}/fontes | `property_sources.*` |
| Documentos | POST /api/imoveis/{id}/documentos (multipart) | `documents`/`document_versions` |

### Atomicidade e dados ausentes
- Cadastro é transacional; processamento de documentos e análise de IA são etapas distintas (não entram na transação do cadastro).
- Só nome, cidade, UF e tipo são obrigatórios. Campos desconhecidos ficam ausentes (nunca inventados).

### Testes
- `tests/test_cadastro_completo.py` (novo): cadastro completo persiste todas as entidades; aparece na lista; cadastro mínimo; validação de título; fontes por endpoint dedicado; integração cadastro → dossiê → análise (gera versão + histórico + financeiro).
- Fixture de referência: **COND PARQUE ARVOREDO RESIDENCIAL CLUBE** (dados reais usados apenas como caso de validação; não hardcoded no produto).
- Frontend: `PropertyWizard.test.tsx` (novo) + ajustes em `PropertiesPage.test.tsx` e `PropertyDetailPage.test.tsx`.
- Resultado: **`pytest -q` = 227 passed** (era 221; +6 novos). **Vitest = 88 passed** (16 arquivos). `alembic upgrade head` aplica 0009 em banco limpo.

### Caso de validação do primeiro E2E real
- O imóvel COND PARQUE ARVOREDO foi preparado como caso de validação do primeiro fluxo E2E real. **O E2E real da Caixa NÃO é declarado concluído** nesta Task — apenas o cadastro foi preparado para esse caso.

### Limitações conhecidas
- A análise continua funcionando sem LLM configurada (comportamento atual preservado); as etapas de IA ficam limitadas sem chave.
- Upload de documentos por URL externa não é baixado automaticamente: a URL é preservada como fonte e o usuário pode fazer upload do arquivo.


## TASK 63 — Ajustes finais do cadastro: data/hora do leilão e feedback de upload
- Objetivo: dois ajustes corretivos identificados na auditoria da TASK 62, antes do E2E real da Caixa. Sem nova arquitetura, sem tocar em LangGraph/agentes/RAG/Risk/Verdict/Checklist/histórico, sem nova tabela.

### 1) Preservar data + hora do 1º e 2º leilão
- Problema: o wizard usa `datetime-local` (ex.: 28/09/2026 10:00), mas os campos eram `DATE`, truncando a hora.
- `backend/app/models.py`: `Auction.first_auction_date` e `Auction.second_auction_date` passaram de `Date` para `DateTime`.
- `backend/app/schemas.py`: `AuctionCreate` e `AuctionFull` passaram `first/second_auction_date` de `date` para `datetime`.
- `backend/migrations/versions/0010_leilao_data_hora.py` (down_revision `0009`): `ALTER COLUMN ... TYPE TIMESTAMP USING (coluna::timestamp)`, preservando os valores existentes. Downgrade converte de volta para `date`.
- `backend/migrations/versions/0001_fundacao_radar.py`: ajuste necessário na "redução ao estado da fundação" (0001 faz `create_all` do schema atual e depois remove o que 0002+ recriam). Adicionadas as colunas de 0009 (`properties.*` novas e `auctions.first/second_auction_*`) e a tabela `property_sources` à lista de remoção, para que `alembic upgrade head` funcione em **banco novo** (antes falhava com `DuplicateColumn`).
- Frontend: `datetime-local` já enviava data+hora sem truncar; o dossiê já exibia via `toLocaleString('pt-BR')`. Sem alteração de contrato no front para este item.

### 2) Feedback de upload de documentos (não esconder falhas)
- Problema: no wizard, uma falha de upload após o cadastro era silenciosamente ignorada.
- `frontend/src/pages/PropertyWizard.tsx`: o cadastro segue transacional e independente do upload. Após criar o imóvel, cada documento é enviado individualmente e contabilizado (`sent`/`failed`). Se algum falhar, o wizard **não navega automaticamente** — mostra um aviso claro (imóvel criado, quantos foram enviados, quais falharam, e que podem ser reenviados pelo Dossiê) com um botão "Ir para o dossiê". Se todos os uploads funcionarem (ou não houver documentos), navega direto ao Dossiê como antes.
- `frontend/src/styles.css`: classe `.wizard-failed-list`.
- O upload continua uma etapa posterior (nunca dentro da transação do cadastro).

### Testes
- `tests/test_cadastro_completo.py`: fixture COND PARQUE ARVOREDO agora com `first_auction_date=2026-09-28T10:00:00` e `second_auction_date=2026-10-02T10:00:00`; asserção de que a hora `10:00` não é truncada; novo `test_leilao_preserva_data_e_hora`.
- `frontend/src/pages/PropertyWizard.test.tsx`: novo teste de upload parcial (imóvel criado, aviso exibido identificando o documento que falhou, navegação só após ação do usuário).
- Resultado: `pytest -q` = **228 passed** (era 227, +1). Vitest = **89 passed** (era 88, +1). `tsc --noEmit` OK.
- Migration validada: `alembic upgrade head` em **banco existente com dados** (0009→0010) e em **banco limpo** (0001→0010; colunas resultam `timestamp without time zone`).

### Escopo preservado
- Fluxo de análise (`POST /api/imoveis/{id}/analisar`) intacto — apenas garantida a ausência de regressão pela mudança de tipo de data.
- Nenhuma nova arquitetura, agente, tabela ou fluxo paralelo. O E2E real da Caixa **não** é declarado concluído.


## TASK 64 — Operação segura local: rebuild, .env, logs e proteção de dados
- Objetivo: base operacional segura antes do E2E real com LLM. Sem tocar em regras de negócio, LangGraph, agentes, RAG, Risk/Verdict/Checklist, histórico ou modelo LLM. Sem infra externa (MinIO/Redis/ELK). Sem reset do banco.

### Rebuild garantido (imagem atual)
- `scripts/start.sh` e `scripts/restart.sh` passaram a usar `docker compose up -d --build`, reconstruindo backend/frontend quando código/Dockerfile mudam. Continuam usando `down` **sem `-v`** — `postgres_data` e `backend_storage` preservados. Mensagens deixam claro que os dados são preservados. `restart.sh` recria os containers, releitura do `.env` (ex.: `OPENAI_API_KEY`).

### Logs operacionais
- Novo `scripts/logs.sh` com `status` (containers/estado/portas/saúde), `tail [servico]`, `follow [servico]` (Ctrl+C não afeta containers) e `save` (snapshot em `logs/radar-<timestamp>.log`).
- `docker-compose.yml`: rotação de logs via `json-file` (`max-size=10m`, `max-file=5`) nos 3 serviços (âncora YAML `x-logging`). Variável `LOG_LEVEL` (padrão INFO) no backend.
- `.gitignore`: `logs/` e `backups/` ignorados.

### Logging detalhado do backend (sem segredos)
- Novo `backend/app/logging_config.py` (`configure_logging` idempotente por `LOG_LEVEL`; namespace `radar.*`).
- Logs adicionados em: cadastro completo e upload (`main.py`), pipeline de documentos — normalização/chunks/versão/erros (`documents/pipeline.py`), RAG — início/filtros/chunks/fallback (`rag/service.py`), LangGraph e agentes — início/versão/domínios/agente/status/evidências (`ai/graph.py`), LLM — provider/modelo/início/fim/erro sanitizado (`ai/gateway.py`).
- Segurança: nenhum segredo é registrado (API key, Authorization, senha, credencial, token). Erros de LLM passam por `sanitize_error`. Conteúdo integral de documentos não é logado (apenas metadados: ids, contagens, status, durações).

### `.env` e proteção do banco
- `.env` permanece a configuração real; `.env.example` só modelo (sem chave). Modelo LLM inalterado (`openai`/`gpt-4o-mini`/`text-embedding-3-small`).
- Nenhuma mudança de schema → **nenhuma migration nova**. Migrations históricas intactas.
- Antes da validação: `./scripts/backup.sh`.

### Documentação
- Novo `docs/OPERATIONS.md` (comandos WSL, rebuild, `.env`, logs, migrations, proteção de dados). `docs/LOCAL-SETUP.md` referencia o guia operacional.

### Validação (ao vivo, WSL2)
- `docker compose config` válido; `docker compose up -d --build` reconstruiu backend/frontend; `health.sh` = 5/5 OK.
- Dados preservados no rebuild/restart: contagem de imóveis/análises/documentos idêntica antes e depois; `alembic_version` inalterado.
- `logs.sh status/tail/save` funcionando; arquivo gerado em `logs/`.
- `OPENAI_API_KEY configurada` confirmado sem exibir a chave.
- `pytest -q` = 228 passed (sem regressão). `alembic upgrade head` sem destruir dados.

## Diagnóstico E2E real — 24/09/2026

Após a TASK 64, foi executada investigação somente leitura no banco para o imóvel Caixa **633**, análise **V4 / analysis_id 189**.

### Evidências de execução

- `llm_runs` registrou 5 agentes: documental, jurídico, financeiro, mercado e checklist.
- Todos os 5 agentes executaram com `provider=openai`, `model=gpt-4o-mini` e `status=CONCLUIDO`.
- Todos receberam exatamente os mesmos 8 chunks: `276, 277, 278, 279, 280, 281, 282, 283`.
- A análise produziu 31 evidências.
- O Checklist possui 27 resultados: 25 `PENDENTE` e 2 `CONFIRMADO`.
- Os 2 confirmados foram `CONSOLIDACAO_REGISTRADA` e `EDITAL_LIDO`, ambos com confiança ALTA e evidência vinculada.

### Diagnóstico documental/RAG

A inspeção dos chunks mostrou que:

- o chunk `276`, associado à matrícula, contém essencialmente dados de autenticidade/CNS e indicação de páginas, caracterizando extração textual insuficiente para a análise registral completa;
- os chunks `277` a `283` representam principalmente o início do edital e contêm dados úteis, como datas dos leilões, comissão, responsabilidade por levantamento/pagamento de débitos, condições de pagamento, regras de habilitação e preço mínimo;
- um único conjunto genérico de 8 chunks não oferece cobertura garantida para as 27 perguntas heterogêneas do Checklist Mestre.

### Conclusão

O diagnóstico não apontou falha geral de LLM, LangGraph ou persistência. O fluxo de execução está funcionando. A limitação principal está na **qualidade da extração documental da matrícula** e na **estratégia de retrieval genérico usada para alimentar o Checklist**.

Foi definida a **TASK 65 — Melhorar Document Intelligence e RAG direcionado para o Checklist**, com foco em:

- detecção de extração textual insuficiente;
- OCR local quando necessário e viável;
- preservação de rastreabilidade;
- retrieval direcionado por grupos/perguntas do Checklist;
- manutenção dos 27 canonical keys;
- ausência de confirmação sem evidência;
- preservação de dados, histórico e versões existentes;
- testes de regressão;
- reanálise controlada do imóvel 633.

Nenhuma alteração de código de produto foi feita durante esse diagnóstico.

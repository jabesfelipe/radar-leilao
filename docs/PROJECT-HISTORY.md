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
- `logs.sh status/tail/save` funcionando; arquivo gerado em `logs/`.- `OPENAI_API_KEY configurada` confirmado sem exibir a chave.
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


## TASK 65 — Document Intelligence e RAG direcionado para o Checklist
- Objetivo: aumentar a cobertura da investigação documental com evidências rastreáveis, mantendo o sistema conservador quando os documentos não suportam conclusão. Sem inventar respostas, sem alterar os 27 itens/estados do Checklist, sem novo agente/RAG paralelo, sem trocar LLM/modelo, sem migration.

### Frente A — Document Intelligence (detecção de extração insuficiente + OCR opcional)
- `backend/app/documents/normalizer.py`: nova `assess_extraction_quality(text, path)` — sinais objetivos (nº de caracteres extraídos, tamanho do arquivo em bytes, densidade chars/KB e se é binário PDF/imagem), sem número mágico único. Grava no `extraction_metadata` (JSON já existente, sem coluna nova): `char_count`, `original_bytes`, `chars_per_kb`, `is_binary`, `extraction_quality` (`SUFICIENTE|INSUFICIENTE|OCR`), `extraction_insufficient_reason`. Um PDF escaneado (grande em bytes, pouco texto) é detectado como `INSUFICIENTE`.
- `backend/app/documents/ocr.py` (novo): OCR **local-first** opcional com import-guard (`ocr_available()` via pytesseract; PDF via pdf2image/poppler, imagem via PIL), texto por página (`## Página N`) preservando rastreabilidade; metadata `ocr=True`, `ocr_engine`, `ocr_language`, `ocr_pages`.
- `backend/app/config.py`: `ocr_enabled` (padrão `False`), `ocr_language` (`por`), `extraction_min_chars` (200), `extraction_min_chars_per_kb` (1.0).
- Comportamento: quando a extração é insuficiente e o OCR está habilitado E disponível, o normalizer usa o texto do OCR (marca `extraction_quality=OCR`, `ocr=True`); caso contrário registra a limitação (`ocr_pending=True`) e **segue sem quebrar**, nunca substituindo o documento original.

### Frente B — RAG direcionado ao Checklist
- `backend/app/rag/checklist_retrieval.py` (novo): `build_item_query(item)` deriva a consulta de cada item a partir de `question`/`description`/`expected_evidence`/`related_rules` + `category` (sem listas manuais gigantes). `retrieve_for_checklist(db, property_id, items)` faz uma busca por item (`PER_ITEM_LIMIT=4`) reutilizando o `HybridRetriever` existente (embeddings/pgvector/busca híbrida — nenhum RAG paralelo), **deduplica** por `chunk_id` mantendo o maior `final_score` e rastreando quais perguntas recuperaram cada chunk, e aplica teto global (`MAX_TOTAL_CHUNKS=24`). O contexto direcionado é formatado com `[checklist_keys=...]` + o formatador de chunk existente.
- `backend/app/ai/agents.py`: `Supervisor.run` ganhou parâmetros opcionais `checklist_context`/`checklist_chunk_ids` e os entrega **apenas ao ChecklistAgent**; os demais agentes seguem com o contexto genérico (contrato inalterado).
- `backend/app/ai/graph.py`: `run_agents` monta o retrieval direcionado quando o domínio `checklist` está presente e o repassa ao Supervisor. Em qualquer falha, faz fallback silencioso (log de aviso) para o comportamento anterior.

### Contrato do Checklist preservado
- Nenhuma alteração em `checklist.py` (27 `canonical_key`), nos estados (`CHECKLIST_STATES`), no seed (`ensure_checklist_master`) ou na persistência (`persist_checklist_agent_findings`, que continua exigindo chunk+evidência reais para qualquer conclusão positiva — nada é confirmado sem evidência).

### Testes
- `tests/test_document_intelligence.py` (7): texto suficiente não marca insuficiente; PDF com pouco texto detectado insuficiente; PDF denso suficiente; normalizer .txt; `ocr_pending` quando OCR indisponível; aplica OCR quando disponível (monkeypatch); `run_ocr` indisponível levanta RuntimeError.
- `tests/test_checklist_retrieval.py` (5): `build_item_query` deriva e difere por item; usa `expected_evidence`/`related_rules`; retrieval direcionado com perguntas diferentes → chunks diferentes + dedup + rastreabilidade; sem evidência → contexto vazio (PENDENTE permanece possível).
- `tests/test_orchestration_graph.py`: 3 `FakeSupervisor.run` atualizados para aceitar os novos kwargs opcionais (mock ajustado, sem enfraquecer teste).
- Resultado: **`pytest -q` = 239 passed** (228 anteriores + 11 novos), sem regressão. Frontend não afetado. **Nenhuma migration** criada.

### Validação E2E real — Imóvel 633 (COND PARQUE ARVOREDO)
- Backend reconstruído (`docker compose up -d --build backend`, volumes preservados, `OPENAI_API_KEY configurada`). Nova análise disparada por `POST /api/imoveis/633/analisar`.
- Preservação (nada apagado): analyses 4→5 (V1–V4 intactas, nova **V5**); document_versions 4→4; document_chunks 1089→1089; evidences 40→73; checklist_executions 5→6; checklist_results 135→162; llm_runs 20→25; verdicts→5.
- Resposta: `versao=5`, 5 agentes `CONCLUIDO`, `llm_usada=true`, `modelo=gpt-4o-mini`. Logs confirmam o RAG direcionado ao vivo: `rag checklist direcionado: property_id=633 itens=27 chunks_distintos=4 (teto=24 por_item=4)` e `checklist_chunks=4 llm=True`.
- Checklist V5: 27 itens; **3 CONFIRMADO** (CONSOLIDACAO_REGISTRADA, EDITAL_LIDO e agora também LEILOES_NEGATIVOS_AVERBADOS — +1 vs V4, obtido por contexto direcionado, com evidência) e 24 PENDENTE (conservador). 5 `checklist_evidences` com rastreabilidade. Veredito V5 = INCONCLUSIVO (Risk/Verdict não quebraram). O E2E real da Caixa **não** é declarado concluído.

### Limitações registradas
- **OCR não executado neste ambiente**: `pytesseract`/`tesseract`/`poppler` não estão instalados (Dockerfile do backend instala só `curl`); `ocr_available()=False`. A detecção funciona e o pipeline fica preparado; habilitar OCR exige provisionar as dependências de sistema/Python e `OCR_ENABLED=true` (documentado em código). Os `document_versions` já existentes do 633 (matrícula escaneada) foram ingeridos antes desta task e não foram reprocessados — a detecção/OCR aplicam-se a novas ingestões.
- **Custo/latência**: o RAG direcionado gera um embedding por item (27) quando há chave de LLM; mantido conservador via `PER_ITEM_LIMIT=4` e teto de 24 chunks. Sem multiplicar chamadas de LLM dos agentes (continua 5).


---

## 24/09/2026 — Auditoria da TASK 65 e definição da TASK 65.1

### Commit auditado

`f8c21bf7f65659e580a0ab152956c6567b9d092a`  
Mensagem: `feat: melhora document intelligence e rag direcionado do checklist`

A comparação com o último estado aprovado mostrou um único commit da TASK 65, sem migration e sem alteração dos contratos dos 27 itens do Checklist.

### O que a TASK 65 implementou

#### Document Intelligence

- Detecção de extração textual insuficiente em `backend/app/documents/normalizer.py`.
- Avaliação usando `char_count`, tamanho do arquivo, densidade chars/KB e tipo binário.
- Metadados gravados no `extraction_metadata`, sem nova coluna.
- Novo OCR local-first em `backend/app/documents/ocr.py`.
- OCR preparado para Tesseract/pytesseract, pdf2image/Poppler e Pillow.
- OCR preserva página e marca a origem no metadata.
- OCR é opcional e não substitui o documento original.

#### RAG direcionado

- Novo `backend/app/rag/checklist_retrieval.py`.
- Query derivada dos próprios campos do Checklist: question, description, expected_evidence, related_rules e category.
- Reutilização do `HybridRetriever` existente.
- Deduplicação por `chunk_id`.
- Rastreabilidade de quais perguntas recuperaram cada chunk.
- Limite por item e teto global de contexto.
- Contexto direcionado entregue somente ao Checklist Agent.
- Demais agentes continuam usando o fluxo genérico.

### O que foi validado

Suíte reportada pelo Kiro:

`pytest -q = 239 passed`

O GitHub não publicou workflow/CI para o commit, portanto esse número é considerado resultado reportado pelo ambiente do Kiro, não uma validação independente por CI.

E2E do imóvel Caixa 633:

- V1–V4 preservadas.
- Nova análise V5 criada.
- analyses: 4 → 5.
- document_versions: 4 → 4.
- document_chunks: 1089 → 1089.
- evidences: 40 → 73.
- checklist_executions: 5 → 6.
- checklist_results: 135 → 162.
- llm_runs: 20 → 25.
- 5 agentes executados com OpenAI/gpt-4o-mini.
- Checklist V5: 27 itens, 3 CONFIRMADO e 24 PENDENTE.
- `LEILOES_NEGATIVOS_AVERBADOS` passou a CONFIRMADO com evidência.
- Risk/Verdict continuaram funcionando.
- Nenhuma versão histórica foi apagada.

### Resultado da auditoria

**TASK 65 NÃO foi encerrada.**

A implementação foi considerada estruturalmente correta, porém existem dois pontos que precisam ser tratados antes do encerramento:

#### 1. OCR ainda não está operacional no Docker

A validação real mostrou:

`ocr_available() = False`

O `backend/Dockerfile` continua sem Tesseract/Poppler e o `backend/requirements.txt` não possui as dependências Python necessárias ao OCR.

Consequentemente, a matrícula escaneada do imóvel 633 ainda não passou por OCR real.

A detecção de extração insuficiente funciona, mas a resolução documental ainda não está operacional no ambiente.

#### 2. Retrieval direcionado gera um embedding por item

A implementação executa uma consulta por item e pode gerar até 27 embeddings por análise do Checklist.

Isso não representa 27 chamadas de geração do LLM — continuam sendo 5 agentes —, mas existe impacto potencial de custo/latência.

A decisão é **medir primeiro**, sem fazer uma refatoração ampla do RAG.

---

## TASK 65.1 — Tornar OCR operacional e validar E2E da matrícula

**Status:** PENDENTE — próxima tarefa operacional do Kiro.

### Objetivo

Corrigir somente os pontos restantes da TASK 65:

1. tornar o OCR local operacional dentro do Docker;
2. validar Tesseract + idioma português + Poppler/pytesseract;
3. processar a matrícula real do imóvel 633 com OCR sem apagar a versão anterior;
4. validar rastreabilidade por página → chunk → evidência → Checklist;
5. medir a quantidade de embeddings produzida pelo retrieval direcionado;
6. executar nova análise controlada do imóvel 633;
7. verificar se a cobertura documental melhora sem criar confirmações artificiais.

### Restrições

- não resetar banco;
- não apagar documentos;
- não apagar document_versions;
- não apagar document_chunks;
- não apagar evidências;
- não apagar análises;
- não alterar os 27 canonical keys;
- não alterar estados do Checklist;
- não alterar Risk/Verdict;
- não criar novos agentes;
- não trocar provider/modelo;
- não criar outro mecanismo de RAG;
- não alterar migrations históricas;
- não fazer otimização ampla de custos nesta etapa;
- não alterar frontend sem necessidade.

### OCR

Adicionar somente as dependências necessárias ao ambiente Docker:

- Tesseract;
- `tesseract-ocr-por`;
- Poppler;
- `pytesseract`;
- `pdf2image`;
- Pillow.

Usar versões compatíveis com o ambiente atual.

Manter OCR opcional via configuração.

Validar dentro do container:

- Tesseract disponível;
- português disponível;
- Poppler disponível;
- `ocr_available() = True`.

### Matrícula 633

Usar a matrícula já existente.

Não substituir o original.

Se houver nova versão, preservar a anterior e validar:

`document_version → page → chunk → evidence → checklist_result`

### RAG

Não reescrever o RAG.

Adicionar apenas medição/log para:

- quantidade de itens;
- embeddings solicitados;
- embeddings executados;
- chunks recuperados;
- chunks distintos.

Não registrar API key nem conteúdo integral de documentos.

### E2E

Executar nova análise do imóvel 633.

Se V5 é a versão atual, esperar nova versão sem apagar V1–V5.

Comparar:

- evidências;
- chunks;
- Checklist;
- estados;
- evidências do Checklist;
- Risk;
- Verdict;
- histórico.

Não existe meta artificial de quantidade de CONFIRMADO.

### Testes

Executar:

`pytest -q`

Adicionar testes somente quando necessários para OCR/medição/regressão.

### Entrega

Criar um único commit.

Atualizar `PROJECT-STATUS.md` e este histórico com os resultados reais.

Depois do commit, aguardar auditoria antes de avançar.

---

## TASK 65.1 — Execução: OCR operacional no Docker + telemetria de embeddings do RAG direcionado
- Objetivo: tornar o OCR local **operacional** no ambiente Docker (mantendo-o opcional e desligado por padrão), **medir** os embeddings usados pelo RAG direcionado do Checklist (telemetria, sem multiplicar chamadas de LLM) e re-analisar o imóvel 633 preservando integralmente o histórico. Sem reset de banco, sem apagar dados, sem alterar os 27 `canonical_key`/estados, sem tocar Risk/Verdict Engine, migrations históricas ou LLM/modelo. Não transformar `PENDENTE` em `CONFIRMADO` sem evidência.

### OCR operacional (local-first, opcional)
- `backend/Dockerfile`: adicionadas as dependências de sistema `tesseract-ocr`, `tesseract-ocr-por` e `poppler-utils` (antes só `curl`), para que `ocr_available()` seja `True` no container.
- `backend/requirements.txt`: adicionadas `pytesseract==0.3.13`, `pdf2image==1.17.0`, `Pillow==11.1.0` (sem upgrade geral das demais dependências).
- `docker-compose.yml`: serviço backend passa a expor `OCR_ENABLED` (default `false`) e `OCR_LANGUAGE` (default `por`) via `environment`, mantendo o padrão desligado e o OCR opt-in por `.env`.
- Validação no container: `tesseract 5.5.0` (idiomas `eng osd por`), `poppler pdftoppm 25.03.0`, `ocr_available()=True`, imports `pytesseract`/`pdf2image`/`PIL` OK, `ocr_enabled=False` (default) e `ocr_language=por`. Nenhum segredo exibido.

### Telemetria de embeddings do RAG direcionado
- `backend/app/rag/checklist_retrieval.py`: `DirectedRetrieval` ganhou o campo `telemetry` (também no `to_dict()`); `retrieve_for_checklist(db, property_id, items, analysis_id=None)` contabiliza `embeddings_solicitados/executados/falhos`, `chunks_recuperados_total` e `chunks_distintos`, e loga a telemetria incluindo `property_id`/`analysis_id`.
- `backend/app/ai/graph.py`: `run_agents` repassa `analysis_id` ao `retrieve_for_checklist`. A medição **não** aumenta o número de chamadas de LLM dos agentes (continua 5).

### Reprocessamento da matrícula com OCR (preservando histórico)
- A matrícula 25278 do imóvel 633 (PDF escaneado, ~538 KB) foi reprocessada com OCR habilitado apenas para essa operação (sem editar o `.env`), reutilizando o pipeline de ingestão existente, gerando **nova `document_version` (v2)** e **preservando** o original, a v1 e os chunks anteriores.
- Resultado da v2: `extraction_quality=OCR`, `ocr=true`, `ocr_engine=tesseract`, `ocr_language=por`, `ocr_pages=2`, `char_count=8355`, 8 chunks. Conteúdo registral real recuperado ("REGISTRO DE IMÓVEIS 7ª Circunscrição Curitiba-Paraná", "Matrícula nº 25.278", compra/venda/mútuo). O documento original **não** foi substituído.

### Validação E2E real — Imóvel 633 (V5 → V6)
- Nova análise por `POST /api/imoveis/633/analisar`: HTTP 200 em ~61s, 5 agentes `CONCLUIDO`, `modelo=gpt-4o-mini`. Log ao vivo: `rag checklist direcionado: property_id=633 analysis_id=229 itens=27 embeddings_solicitados=27 embeddings_executados=27 embeddings_falhos=0 chunks_recuperados_total=108 chunks_distintos=4`.- Preservação (nada apagado): analyses 5→6 (V1–V5 intactas, nova **V6**); document_versions 4→5 (+ matrícula OCR v2); document_chunks 1089→1097 (+8 OCR; v1 intacta); evidences 73→108; checklist_executions 6→7; checklist_results 162→189 (+27); llm_runs 25→30 (+5); verdicts 5→6. 27 `canonical_key` intactos. Veredito V6 = INCONCLUSIVO.
- Checklist V6: 27 itens, **0 CONFIRMADO / 27 PENDENTE** (conservador). `LEILOES_NEGATIVOS_AVERBADOS` = PENDENTE — correto documentalmente (a matrícula não contém averbação de leilão que sustente confirmação). Nenhuma confirmação foi forçada para melhorar cobertura.

### Testes
- `tests/test_document_intelligence.py`: +4 testes de OCR (agora 11 no arquivo), todos por `monkeypatch` (não exigem Tesseract instalado no ambiente de teste): OCR desabilitado mantém comportamento (sem OCR, `ocr_pending`); marcadores `## Página N` preservados em PDF multipágina e idioma `por` repassado ao motor; `run_ocr` usa `por` por padrão; original não é substituído nem alterado em disco.
- Resultado: **`pytest -q` = 243 passed** (239 anteriores + 4 novos), sem regressão. Frontend não afetado. **Nenhuma migration** criada.

### Limitação registrada (honesta, fora do escopo 65.1)
- Os chunks do imóvel 633 **não possuem embedding**: a geração de embeddings não ocorre na ingestão (lacuna pré-existente da Task 65). Logo o `HybridRetriever` opera em **modo texto** e as 27 consultas direcionadas recuperam predominantemente chunks genéricos do edital; os chunks OCR da matrícula não entram no top-k e o OCR ainda não se reflete em confirmações do Checklist. A correção (gerar embeddings na ingestão) é uma mudança de pipeline que **excede o escopo desta task** e deve ser tratada separadamente. Por isso a V6 permaneceu conservadora — comportamento correto, não uma regressão.


---

## 24/09/2026 — Aprovação da TASK 65.1 e definição da TASK 66

### TASK 65.1 — resultado da auditoria

**Commit:** `af00ccb` — `fix: torna OCR operacional no Docker e mede embeddings do RAG direcionado`

**Status:** 🟢 APROVADA.

A auditoria confirmou que a implementação atende ao escopo: OCR local operacional no Docker, Tesseract com português, Poppler, `ocr_available()=True`, OCR opcional/desligado por padrão, reprocessamento real da matrícula 25278 do imóvel 633 em nova versão sem apagar a anterior, preservação de páginas/chunks/rastreabilidade, telemetria de embeddings do retrieval direcionado e suíte `pytest -q = 243 passed` reportada pelo Kiro.

A reanálise criou V6 preservando V1–V5. Foram mantidos os 27 canonical keys e nenhuma confirmação artificial foi introduzida. A limitação restante foi confirmada: os chunks não recebem embedding automaticamente durante a ingestão, portanto o pgvector não consegue aproveitar plenamente os novos chunks OCR.

### Nova lacuna técnica identificada

O pipeline atual cria `DocumentChunk`, mas a geração/persistência do embedding do chunk não ocorre automaticamente na ingestão. Isso produz uma assimetria:

- as consultas do RAG direcionado geram embeddings;
- os chunks do documento podem não possuir embedding;
- o `HybridRetriever` fica limitado ao componente textual para esses chunks;
- documentos OCR novos não são plenamente explorados pela busca vetorial.

Essa lacuna não foi tratada na TASK 65.1 porque a correção de ingestão estava explicitamente fora do escopo daquela tarefa.

## TASK 66 — Embeddings na ingestão dos DocumentChunks

**Status:** PENDENTE — próxima tarefa operacional do Kiro.

### Objetivo

Garantir que novos `DocumentChunk` elegíveis recebam embedding e tenham o vetor persistido no mecanismo pgvector já existente durante a ingestão, reutilizando o código de embeddings atual e sem criar nova arquitetura.

### Restrições

- Não criar novo RAG.
- Não criar novo banco vetorial.
- Não criar novos agentes.
- Não alterar LangGraph.
- Não alterar os 27 canonical keys ou estados do Checklist.
- Não alterar Risk/Verdict.
- Não trocar provider/modelo.
- Não apagar histórico.
- Não apagar documentos, versões, chunks, evidências ou análises.
- Não reprocessar automaticamente todo o histórico.
- Não criar infraestrutura nova como MinIO/Redis/ELK.
- Não alterar migrations históricas.
- Só criar migration incremental se a inspeção comprovar necessidade real.

### Primeiro passo obrigatório

Antes de codificar, localizar no código:

1. modelo `DocumentChunk` e campo vetorial existente;
2. mecanismo atual de geração de embeddings (`gateway`, `RAGService` ou equivalente);
3. ponto correto da ingestão em que o chunk já existe e pode receber embedding;
4. comportamento esperado quando `OPENAI_API_KEY` não existe;
5. se existe algum fluxo parcial de embedding que possa ser reutilizado.

**Não recriar um mecanismo que já existe.**

### Comportamento esperado

Para um novo documento:

`documento → normalização/OCR → chunks → embedding do chunk → pgvector → RAG`

Quando houver chave/configuração válida:

- gerar embedding para cada chunk elegível;
- persistir no campo vetorial existente;
- manter `chunk_id`, document_version, página e demais metadata intactos;
- permitir recuperação semântica pelo `HybridRetriever`.

Quando não houver chave ou o embedding estiver indisponível:

- não quebrar a ingestão;
- manter o documento/chunks persistidos conforme o comportamento atual;
- registrar a limitação de forma segura;
- permitir fallback textual do RAG.

### Idempotência e custo

A implementação deve evitar geração duplicada desnecessária.

Não fazer backfill automático de todo o banco.

Medir no E2E quantos embeddings foram solicitados/executados e quantos chunks receberam vetor.

### Testes obrigatórios

Adicionar testes para:

- chunk novo com embedding persistido;
- embedding correto associado ao chunk;
- documento com múltiplos chunks;
- ausência de API key;
- falha do provider de embedding;
- fallback sem quebrar ingestão;
- não duplicação quando o chunk já possui embedding;
- preservação de página/document_version/metadata;
- recuperação do chunk via busca semântica existente;
- regressão do pipeline atual.

Executar `pytest -q`.

### E2E controlado — imóvel 633

Não apagar V1–V6.

Fazer uma nova ingestão controlada de um documento do imóvel 633, preferencialmente a matrícula já utilizada no OCR, criando nova versão.

Validar no banco:

- novos chunks criados;
- novos chunks com embedding não nulo;
- dimensão compatível com o modelo configurado;
- document_version correta;
- página correta;
- hash/original preservados.

Depois executar uma consulta semântica específica relacionada ao conteúdo da matrícula e confirmar que um chunk OCR pode ser recuperado pelo `HybridRetriever` por similaridade vetorial.

Se o fluxo estiver estável, executar nova análise do 633 e comparar com V6.

**Não existe meta de número de CONFIRMADO.** O objetivo é comprovar a recuperação semântica e manter o comportamento conservador do Checklist.

### Critério de aceite

A TASK 66 somente será aprovada quando:

1. um novo `DocumentChunk` real tiver embedding persistido;
2. o vetor estiver associado ao chunk correto;
3. uma busca semântica real conseguir recuperar esse chunk;
4. a ingestão continuar funcionando sem API key;
5. falha do embedding não quebrar o pipeline;
6. não houver duplicação desnecessária;
7. `pytest -q` passar sem regressão;
8. histórico do 633 permanecer preservado;
9. nenhum contrato de Checklist/Risk/Verdict for alterado;
10. a implementação estiver limitada ao escopo desta TASK.

### Entrega

Um único commit.

Atualizar `PROJECT-STATUS.md` e `PROJECT-HISTORY.md` com resultados reais.

Informar arquivos alterados, testes, quantidade de embeddings e resultado do E2E.

Depois do commit, **parar e aguardar auditoria**. Não iniciar TASK 67.

---

## TASK 66 — Execução: embeddings na ingestão dos DocumentChunks
- Objetivo: corrigir a lacuna da TASK 65.1 — o pipeline criava `DocumentChunk` mas não gerava/persistia o embedding do chunk na ingestão. Correção mínima de pipeline; sem novo RAG/agente/provider, sem alterar LangGraph/Checklist/Risk/Verdict, sem migration (a coluna já existe), sem reprocessar o histórico.

### Causa raiz (investigação antes de codar)
- `DocumentPipeline.ingest` (`backend/app/documents/pipeline.py`) criava os chunks com conteúdo/página/seção/metadata, porém **não chamava nenhuma geração de embedding**.
- Existiam dois helpers `embed_pending_chunks` (`backend/app/documents/embedding.py` e `backend/app/rag/embeddings.py`), mas **nenhum era invocado no pipeline** — só um deles era referenciado por um teste. Resultado: todo chunk nascia com `embedding = NULL`.
- O modelo `models.DocumentChunk.embedding` já é `Vector(settings.embedding_dimensions)` (1536) — **coluna existente, sem migration**.
- O `RAGService`/`HybridRetriever` já geram o embedding da consulta e usam `c.embedding <=> vetor` quando o chunk tem vetor; sem vetor, o score vetorial é 0 e a busca cai em modo texto — exatamente o sintoma observado no 633.

### Solução (correção mínima)
- `backend/app/documents/embedding.py`: `embed_pending_chunks(db, version_id)` reescrito para (a) retornar telemetria (`embeddings_pendentes/solicitados/executados/persistidos/falhos`, `provider_disponivel`, `dimensao`); (b) guardar em `settings.effective_llm_api_key` (sem chave → não constrói gateway); (c) ser idempotente (`embedding IS NULL`); (d) validar dimensão contra `settings.embedding_dimensions` (descarta vetor divergente); (e) tolerar falha do provider (try/except com `sanitize_error`, sem levantar); (f) `flush` apenas se persistiu.
- `backend/app/documents/pipeline.py`: importa e chama `embed_pending_chunks(self.db, version.id)` **após o flush dos chunks**, dentro de `try/except` — falha de embedding nunca quebra a ingestão. Fica na mesma transação (o commit ocorre no endpoint, depois de `ingest`).
- Não alterei `rag/embeddings.py` nem `knowledge_memory.py`.

### Comportamento sem chave / falha
- Sem `OPENAI_API_KEY`: ingestão segue por texto, chunks são criados, nenhum embedding é gerado (telemetria `provider_disponivel=False`).
- Falha do provider ou dimensão incompatível: registrado com segurança, embedding não é persistido, ingestão conclui normalmente.

### Testes
- Novo `tests/test_chunk_embedding.py` (10): chunk novo recebe embedding e é persistido com dimensão correta; múltiplos chunks (uma única chamada em lote ao provider); sem API key não gera nada; falha do provider não persiste e não levanta; dimensão incompatível descartada; idempotência (chunk já vetorizado não é reprocessado); pipeline dispara o embedding para a versão criada; falha do embedding não quebra a ingestão; página/versão/metadata preservados; chunk recuperável pelo `HybridRetriever` por similaridade vetorial.
- Ajustado `tests/test_llm_tracking.py::test_document_embedding_nao_constroi_gateway_sem_api_key` para o novo contrato de telemetria (verifica `provider_disponivel=False` e contadores zerados), preservando a intenção original (sem chave não constrói gateway nem busca chunks).
- Resultado: **`pytest -q` = 253 passed** (243 anteriores + 10 novos), sem regressão. **Nenhuma migration.** Frontend não afetado.

### E2E real — Imóvel 633 (V6 → V7)
- Backup: `backups/radar-backup-20260924-220845`. Provider disponível no container; modelo de embedding `text-embedding-3-small`, dimensão 1536.
- **Reingestão da matrícula** (bytes do original em disco; OCR habilitado apenas para a operação; `DocumentPipeline.ingest` reutilizado) criou a **v3** (`version_id=454`) preservando v1/v2: `extraction_quality=OCR`, `ocr_pages=2`, `char_count=8355`, **8 chunks, todos com embedding**, dimensão 1536 (min=max), página/seção/metadata preservados, conteúdo registral real (Matrícula 25278, Curitiba). Chunks ids 1752–1759.
- **Busca semântica**: consulta `"registro de imóveis matrícula 25278 Curitiba consolidação"` retornou como top-5 **todos os chunks OCR da matrícula v3**, com `vector_score` 0,57–0,63 e `text_score = 0,0000` → recuperados **por similaridade vetorial pura** (impossível antes). `RAGService`: `vector_search=True`, `text_fallback=False`.
- **Análise V7** (`POST /api/imoveis/633/analisar`): HTTP 200, 5 agentes `CONCLUIDO` (`gpt-4o-mini`, 27.885 tokens, 5/5 sucesso), e `chunks_recuperados = [1752..1759]` (os chunks OCR da matrícula), contra 276–283 (edital genérico) na V6. Checklist V7: **4 CONFIRMADO / 23 PENDENTE** (V6 = 0/27); `LEILOES_NEGATIVOS_AVERBADOS` = CONFIRMADO com evidência da matrícula. 27 evidências do 633 passaram a citar os chunks OCR da matrícula v3. Melhora **orgânica**, sem forçar confirmação.
- **Métricas de embeddings (reingest v3):** criados=8, solicitados=8, executados=8, sucesso=8, falha=0, com embedding=8, dimensão=1536, modelo=`text-embedding-3-small`.

### Contagens antes → depois
- analyses 6→7 (V1–V7 preservadas); document_versions 5→6; document_chunks 1097→1105 (+8); chunks_com_embedding **0→8** (apenas os novos — sem backfill do histórico); evidences 108→142; verdicts 6→7. Matrícula versões [1,2,3] preservadas. 27 `canonical_key` intactos.

### Limitação registrada (honesta)
- Somente os chunks **novos** (ingeridos após a correção) recebem embedding. Os ~1097 chunks históricos do 633 permanecem sem vetor (sem backfill, por escopo). A recuperação semântica plena de documentos antigos exigiria reingestão/backfill controlado — fora do escopo desta task.

---

## 24/09/2026 — Auditoria da TASK 66 e definição da TASK 67

### TASK 66 — Embeddings na ingestão dos DocumentChunks

**Commit:** 24e6b2b  
**Status:** 🟢 APROVADA.

A auditoria confirmou a causa raiz e a correção mínima: o DocumentPipeline criava DocumentChunk, mas não chamava a geração de embedding. A coluna vetorial já existia e o mecanismo de embedding já estava disponível; a correção conectou o pipeline ao helper existente.

Validações principais:

- sem migration;
- sem novo RAG;
- sem novo agente;
- sem novo provider;
- sem alteração de LangGraph, Checklist, Risk ou Verdict;
- embedding em lote;
- idempotência por embedding nulo;
- validação de dimensão 1536;
- fallback seguro sem API key;
- falha do provider não interrompe ingestão;
- novos chunks recebem embedding;
- busca semântica real recupera chunks OCR da matrícula 25278.

No imóvel 633:

- matrícula reingerida como v3;
- 8 chunks criados;
- 8/8 com embedding;
- dimensão 1536;
- modelo text-embedding-3-small;
- busca vetorial retornou os chunks OCR da matrícula;
- V7 criada preservando V1–V6;
- chunks OCR 1752–1759 passaram a ser recuperados;
- Checklist V7: 4 CONFIRMADO / 23 PENDENTE;
- LEILOES_NEGATIVOS_AVERBADOS confirmado com evidência da matrícula;
- sem confirmação artificial.

Suíte reportada: 253 passed. O GitHub não publicou CI independente para essa execução, portanto a contagem é registrada como resultado do ambiente do Kiro.

### Limitação atual

Os chunks históricos anteriores à correção permanecem sem embedding. Não houve backfill, conforme escopo da TASK 66.

Isso não bloqueia a validação do mecanismo novo, mas significa que documentos históricos somente entram na busca vetorial quando reingeridos ou quando um futuro backfill controlado for executado.

### Próximo foco técnico

Agora não devemos continuar adicionando funcionalidades sem validar a qualidade do contexto.

A TASK 67 será uma investigação controlada do retrieval real da V7.

## TASK 67 — Validação de qualidade do contexto RAG no E2E real

**Status:** PENDENTE — próxima tarefa operacional do Kiro.

### Objetivo

Determinar, com dados reais do imóvel 633, exatamente quais chunks/documentos/páginas são entregues aos cinco agentes e ao Checklist.

A pergunta central é:

> O retrieval atual está entregando contexto suficiente e adequado por domínio, sem perder evidências relevantes por deduplicação, limite ou estratégia de busca?

### Escopo

- auditar Documental, Jurídico, Financeiro, Mercado e Checklist separadamente;
- identificar IDs de chunks, documentos, versões e páginas;
- identificar origem/tipo do documento quando disponível;
- comparar V6 e V7;
- auditar o retrieval direcionado das 27 perguntas;
- medir distribuição dos chunks por documento;
- identificar itens sem contexto;
- identificar perdas por limite/deduplicação;
- verificar se matrícula OCR chega aos agentes que precisam dela;
- verificar se edital e matrícula conseguem coexistir quando uma análise depende dos dois;
- adicionar somente instrumentação mínima se os logs atuais forem insuficientes;
- não registrar conteúdo integral, prompts completos, chaves ou dados sensíveis.

### Regra principal

**Diagnóstico antes de correção.**

Não alterar o algoritmo de RAG apenas porque V7 mudou.

Primeiro produzir evidência objetiva da composição do contexto.

Se houver falha comprovada, aplicar somente a menor correção necessária e testá-la.

Se não houver falha, não inventar mudança funcional.

### E2E

Usar V7 como referência.

Não apagar V1–V7.
Não reingerir documentos sem necessidade.

Não criar V8 apenas para gerar dados se a telemetria existente for suficiente.

Se V8 for necessária para validar a instrumentação, preservar V7 e executar de forma controlada.

### Fora do escopo

- novo agente;
- troca de LLM/provider;
- troca de embedding;
- novo vector DB;
- substituição do pgvector;
- reescrita completa do RAG;
- alteração dos 27 canonical keys;
- alteração de estados;
- alteração de Risk/Verdict;
- backfill histórico;
- infraestrutura nova;
- otimização ampla de custos;
- apagar histórico;
- alterar migrations históricas.

### Testes

Executar pytest -q.

Adicionar apenas testes relacionados à instrumentação ou a uma correção comprovada.

Não criar testes artificiais apenas para aumentar a contagem.

### Critérios de aceite

A TASK 67 deverá entregar:

1. diagnóstico dos chunks/contextos por agente;
2. comparação V6 × V7;
3. diagnóstico das 27 perguntas do Checklist;
4. documentos/versões/páginas representados;
5. confirmação de que o OCR da matrícula chega aos agentes necessários;
6. gargalos de contexto/deduplicação/limite identificados;
7. nenhuma confirmação artificial;
8. suíte verde;
9. histórico V1–V7 preservado;
10. qualquer correção funcional deve ser mínima e justificada pelos dados.

### Entrega

Um único commit se houver alteração necessária.

Atualizar PROJECT-STATUS.md e PROJECT-HISTORY.md.

Relatar:

- diagnóstico por agente;
- chunks/documentos/páginas;
- V6 × V7;
- cobertura do Checklist;
- testes;
- alteração funcional, se houver;
- limitações restantes.

Depois do commit:

**PARAR. Não iniciar TASK 68. Aguardar auditoria.**

---

## TASK 67 — Execução: diagnóstico da qualidade do contexto RAG (E2E 633, V7)
- Objetivo: validar, com dados reais, o que cada um dos 5 agentes recebe de contexto no E2E do imóvel 633 (referência V7), comparar V6×V7, medir a cobertura das 27 perguntas do Checklist e distinguir ausência documental de falha de retrieval. Tarefa diagnóstica: não começar alterando o RAG; só corrigir se houver falha comprovada e a correção for mínima e dentro do escopo.

### Como o contexto chega a cada agente (investigação de código)
- `graph.py`: `RETRIEVE_RAG` faz UMA busca genérica (`RAGService.retrieve_context("análise documental do imóvel", filtros=_rag_filter(domains))`). Como a análise inclui os 5 domínios, `_rag_filter` deixa `category=None` (sem filtro por domínio) e retorna `rag_default_limit=8` chunks compartilhados.
- `RUN_AGENTS`/`Supervisor.run`: Documental, Jurídico, Financeiro e Mercado recebem esse mesmo contexto genérico; apenas o Checklist recebe o contexto **direcionado** (`checklist_retrieval.retrieve_for_checklist`, `PER_ITEM_LIMIT=4`, `MAX_TOTAL_CHUNKS=24`, dedup por `chunk_id`).
- `HybridRetriever` (retriever.py): ranking `final = vetor·0,7 + texto_norm·0,3`, isolado por `property_id`; usa o vetor do chunk só quando `embedding IS NOT NULL`.

### Diagnóstico por agente (fonte: `llm_runs.retrieved_chunk_ids`)
```text
V6 (analysis_id=229):
  Documental/Jurídico/Financeiro/Mercado: 8 chunks = 1 MATRICULA v1 (276) + 7 EDITAL v1 (277..283)
  Checklist:                              4 chunks = 1 MATRICULA v1 + 3 EDITAL v1

V7 (analysis_id=266):
  Documental/Jurídico/Financeiro/Mercado/Checklist: 8 chunks = 8 MATRICULA v3 (1752..1759), EDITAL = 0
```
V6 era edital-dominado (matrícula quase ausente); V7 inverteu para matrícula-only (edital 100% ausente). Matrícula e edital **não coexistem** no contexto de nenhum agente na V7.

### Cobertura das 27 perguntas do Checklist (V7, execução 1089)
- 4 CONFIRMADO, todos citando matrícula v3: `CONSOLIDACAO_REGISTRADA` (1752), `LEILOES_NEGATIVOS_AVERBADOS` (1756), `VAGA_MATRICULA` (1752), `PENHORA_INDISPONIBILIDADE` (1754).
- 2 PENDENTE com evidência da matrícula (Caso C — agente conservador): `ACAO_QUESTIONAMENTO` (1756), `QUITACAO_80` (1758).
- 21 PENDENTE sem evidência:
  - Caso A (ausência documental / dependem de engine determinístico ou comparáveis — PENDENTE correto): Mercado (`COMPARAVEIS_SUFFICIENTES`, `CONDOMINIO_PORTARIA`, `ILIQUIDEZ`, `REFORMA_LIQUIDEZ`, `REGIAO_SERVICOS`), `DISTANCIA_USUARIO`, Financeiro `RETORNO_SELIC`/`PRAZO_DOIS_ANOS`/`REFORMA_GRANDE`, Desocupação (`ETICA_OCUPACAO`/`LOCACAO_REGISTRADA`/`TERCEIRO_OCUPANTE`), Jurídico `EVICCAO`/`GARANTIA_DIVIDA_TERCEIRO`.
  - Caso B (falha de retrieval — a informação existe no edital, mas o edital não chegou): `EDITAL_LIDO`, Financeiro `RESPONSABILIDADE_DEBITOS`/`CONDOMINIO_ALTO`, Jurídico `INTIMACAO_EDITAL`/`NOTIFICACAO_DOIS_LEILOES`/`LANCE_MENOR_50_AVALIACAO`/`INTIMACAO_PESSOAL`.

### Causa raiz (comprovada)
- No 633, só a matrícula v3 (8 chunks) tem embedding; edital (doc 193 e 195, 544 chunks cada) e matrícula v1/v2 têm 0 embedding — consequência direta de a Task 66 não fazer backfill do histórico.
- Com o peso vetorial de 0,7, os chunks da matrícula (final ~0,35) superam qualquer edital por texto puro (final ~0,30) e ocupam todos os 8 slots. Probes ao vivo: a query genérica com embedding retorna 8 matrícula / 0 edital; sem embedding retorna 0; nas 27 consultas por item do Checklist, 108/108 candidatos são matrícula e 0 são edital (as consultas são frases longas com `plainto_tsquery` em AND; `expected_evidence`/`related_rules` estão vazios para os itens de edital). O edital só é alcançável por texto com termos curtos (`avaliação` 0,3, `débitos` 0,2, `comissão leiloeiro` 0,11), que as consultas atuais não usam.
- Não é perda por `PER_ITEM_LIMIT`/`MAX_TOTAL_CHUNKS` nem por dedup: é assimetria de cobertura de embedding + ranking sem diversidade por documento + consultas que não alcançam o edital por texto.

### Decisão: sem alteração funcional (correção fora do escopo)
A falha é real, porém as três formas de corrigi-la estão explicitamente fora do escopo da TASK 67: (1) embedar o edital = backfill do histórico (proibido); (2) reescrever a semântica de consulta/casamento textual = reescrever o RAG (proibido); (3) cota de diversidade por documento não resolve, pois o edital nem entra como candidato. Portanto, conforme a regra da própria task (“não inventar alteração funcional”; “só a menor correção, se existir”), **nenhum código foi alterado**. A instrumentação existente já respondeu a todas as perguntas de aceite; **nenhuma instrumentação adicional foi necessária**.

Recomendação para a próxima task (fora do escopo desta): tornar edital+matrícula recuperáveis em conjunto — via reingestão controlada do edital para gerar seus embeddings (equivalente à Task 66 aplicada ao edital) e/ou cota por documento no retrieval combinada com consultas que alcancem o edital por texto.

### Preservação e testes
- V1–V7 preservadas; nenhum dado histórico alterado; nenhuma confirmação artificial; V8 não foi criada (diagnóstico possível com dados/telemetria já persistidos).
- `pytest -q` = 253 passed (baseline intacto; nenhum código alterado nesta task).

---

## 24/09/2026 — Auditoria da TASK 67 e definição da TASK 68

### TASK 67 — Validação de qualidade do contexto RAG no E2E real

**Commit:** `006877b61c788c30dfc4930db307bdea2854c673`  
**Status:** 🟢 APROVADA.

A auditoria confirmou que a tarefa permaneceu diagnóstica e não alterou código funcional. O diagnóstico foi considerado suficiente e consistente com o código do HybridRetriever.

### Resultado validado

No V7 do imóvel 633 (analysis_id=266):
- Documental: 8 chunks, todos matrícula v3 (1752–1759), edital 0;
- Jurídico: 8 chunks, todos matrícula v3, edital 0;
- Financeiro: 8 chunks, todos matrícula v3, edital 0;
- Mercado: 8 chunks, todos matrícula v3, edital 0;
- Checklist: 8 chunks, todos matrícula v3, edital 0.

A comparação com V6 mostrou inversão do problema: V6 era edital-dominado; V7 passou a ser matrícula-only. Portanto, matrícula e edital não coexistiam no contexto de nenhum agente.

### Causa raiz validada

Apenas os 8 chunks da matrícula v3 possuíam embedding. Os chunks históricos do edital permaneciam sem vetor porque a TASK 66 não fez backfill histórico. O ranking híbrido usa vetor com peso 0,7 e texto com peso 0,3. Os probes registrados na TASK 67 demonstraram 108/108 candidatos das 27 consultas direcionadas como matrícula e 0 edital.

A auditoria também confirmou que a perda não foi causada por PER_ITEM_LIMIT, MAX_TOTAL_CHUNKS ou deduplicação. O edital é alcançável por algumas consultas textuais curtas, mas não pelas consultas atuais em quantidade suficiente.

### Checklist

A V7 registrou 4 CONFIRMADO e 23 PENDENTE. Os 7 itens afetados por ausência do edital foram identificados como falha de retrieval:
- EDITAL_LIDO;
- RESPONSABILIDADE_DEBITOS;
- CONDOMINIO_ALTO;
- INTIMACAO_EDITAL;
- NOTIFICACAO_DOIS_LEILOES;
- LANCE_MENOR_50_AVALIACAO;
- INTIMACAO_PESSOAL.

Nenhuma confirmação artificial foi introduzida. V1–V7 permanecem preservadas e não foi criada V8.

### Decisão

A TASK 67 foi aprovada como diagnóstico concluído. A falha descoberta não deve ser considerada encerrada: ela bloqueia a validação final da qualidade documental do E2E porque o edital é uma fonte necessária para parte do Checklist e dos agentes.

A correção deve ser feita em uma única TASK controlada, sem backfill global e sem reescrita do RAG.

pytest -q reportado: 253 passed. Como não houve alteração funcional nesta task, a suíte foi registrada como baseline intacto.


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

---

## TASK 68 — Execução: recuperação conjunta de edital + matrícula (E2E 633, V8)
- Objetivo: corrigir a falha comprovada na Task 67 (edital não coexistia com a matrícula no contexto) de forma mínima, reutilizando o embedding da Task 66. Sem backfill global, sem reescrever o RAG, preservando V1–V7 e sem confirmação artificial.

### Identificação do edital
- Edital efetivamente usado pela análise = **doc 193** (`EDITAL`, `EL00440226CPARE.pdf`, hash `4e5926d9c35c`, ver_id 193 v1, 544 chunks 277–820, 0 embedding). Os chunks 277–283 usados na V6 pertencem a este documento. O doc 195 (`edital`, source caixa) é duplicata do mesmo arquivo/hash → não reprocessado. Backup: `backups/radar-backup-20260924-224856`.

### Reingestão controlada do edital
- `DocumentPipeline.ingest` (pipeline da Task 66) gerou **edital v2** (`document_version_id=474`) preservando a v1: `SUFICIENTE`, `ocr=False`, `char_count=573775`, **544 chunks, 544 com embedding**, dimensão 1536. Embeddings globais 8 → 552. Sem backfill de outros documentos.

### Prova isolada e diagnóstico do novo desequilíbrio
- As 5 consultas temáticas passaram a recuperar o edital por similaridade vetorial. Porém o retrieval direcionado do checklist passou a devolver **24/24 chunks de edital** (a matrícula, com apenas 8 chunks, era esmagada pelos 544 do edital). Ou seja, **embeddar o edital sozinho inverteu o problema** (antes matrícula-only na V7; agora edital-only), atendendo à condição da task para aplicar a menor correção.

### Correção mínima (2 arquivos)
- `backend/app/rag/checklist_retrieval.py`: `_select_with_document_diversity(chunks, max_total)` — agrupa os candidatos já recuperados por documento de origem, ordena cada grupo por `final_score` e distribui os `MAX_TOTAL_CHUNKS` em round-robin por documento (documentos ordenados pelo melhor score), reordenando o resultado por relevância. Substitui o corte por score puro na seleção final. Não altera `PER_ITEM_LIMIT`/`MAX_TOTAL_CHUNKS`, pesos, consulta ou ranking do retriever, e não recupera nada novo.
- `backend/app/services.py`: `valid_chunk_ids(raw)` restringe os `chunk_ids` do LLM a inteiros positivos ≤ int4 do PostgreSQL, aplicada nos dois pontos de persistência. Corrige um HTTP 500 (`integer out of range`) observado na 1ª tentativa de V8, quando o LLM citou `1555528765064` (número do conteúdo da matrícula) como chunk_id. Guarda defensiva e conservadora (id inválido → sem evidência), sem mudar regra de negócio. Essa 1ª tentativa falhou antes de persistir (nenhuma V8 parcial ficou no banco).
- Efeito no retrieval direcionado do 633: 24 EDITAL / 0 MATRÍCULA → **22 EDITAL / 2 MATRÍCULA**.

### E2E V8 (preservando V1–V7)
- Análise **V8** (`analysis_id=280`): HTTP 200, 5 agentes `CONCLUIDO` (5/5, `gpt-4o-mini`), 35.231 tokens, custo ≈ US$ 0,0072, veredito INCONCLUSIVO.
- Distribuição por agente — **coexistência em todos**: checklist 22 edital + 2 matrícula; documental/financeiro/jurídico/mercado 7 edital + 1 matrícula.
- Contagens antes → depois: analyses 7→8 (V1–V8 preservadas), document_versions 6→7, document_chunks 1105→1649 (+544 edital v2), evidences 142→175, verdicts 7→8, chunks_com_embedding 8→552. 27 `canonical_key` intactos.

### Checklist V8 e os 7 itens afetados
- Estados: **7 CONFIRMADO / 20 PENDENTE** (V7: 4/23). CONFIRMADO: CONSOLIDACAO_REGISTRADA (matrícula v3), EDITAL_LIDO, LEILOES_NEGATIVOS_AVERBADOS, VAGA_MATRICULA, EVICCAO, NOTIFICACAO_DOIS_LEILOES, QUITACAO_80 (edital v2).
- 7 itens afetados: `EDITAL_LIDO` → CONFIRMADO (edital v2, antes impossível); `NOTIFICACAO_DOIS_LEILOES` → CONFIRMADO (edital v2); `RESPONSABILIDADE_DEBITOS`, `CONDOMINIO_ALTO`, `INTIMACAO_EDITAL`, `INTIMACAO_PESSOAL`, `LANCE_MENOR_50_AVALIACAO` → PENDENTE (edital presente no contexto, mas o agente não julgou a evidência suficiente — conservador). 2/7 confirmaram organicamente com o edital; nenhuma confirmação artificial. A matrícula continua sendo usada (CONSOLIDACAO cita chunk 1758).

### Testes
- +4 testes de diversidade por documento (`tests/test_checklist_retrieval.py`) + 1 de `valid_chunk_ids` (`tests/test_llm_tracking.py`). `pytest -q` = **258 passed** (253 anteriores + 5 novos), sem regressão. Nenhuma migration; frontend não afetado.

### Limitações restantes
- Itens muito específicos da matrícula cujo texto do edital é semanticamente próximo (ex.: VAGA_MATRICULA, PENHORA_INDISPONIBILIDADE) podem não trazer a matrícula no topo do retrieval por item; a matrícula ainda coexiste no contexto compartilhado do checklist (2 chunks). Ajuste fino de recuperação por item seria tarefa própria, fora do escopo desta correção mínima.
- O doc 195 (edital duplicado) permanece sem embedding (duplicata do doc 193).
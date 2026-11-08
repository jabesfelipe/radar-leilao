# Radar Leilão — Consolidação do MVP (2026-11)

> **Escopo desta rodada:** auditoria real do produto (Fase 0) + **Onda 11 — Autenticação
> e RBAC real** implementada, integrada e testada. As demais frentes do ciclo
> (modalidades completas, ciclo de vida de workflow ponta-a-ponta, enriquecimento do
> dashboard) foram **auditadas e diagnosticadas** aqui, com estado honesto e pendências
> explícitas — ver §9. Nada foi marcado como concluído sem teste verde.
>
> **Validação (banco descartável pgvector):** backend **729 passed / 2 skipped**;
> frontend **tsc OK + 148 passed / 25 arquivos**; migrations `upgrade head` (0023) →
> `downgrade 0022` → `re-upgrade` RC=0; contrato OpenAPI **123 paths**.

Base: branch `main`. Alembic head = `0023_usuarios`.

---

## 1. Arquitetura final (resumo)

- **Backend** FastAPI + SQLAlchemy 2.0 + Alembic + PostgreSQL/pgvector. App module-level
  (`backend/app/main.py`), routers por domínio (`health`, `hubs`, `legal_central`,
  `market`, `admin`, `debts`, **`auth`**) + endpoints inline do dossiê.
- **Identidade/RBAC** (novo): `auth.py` (hashing bcrypt, JWT HS256, `get_current_user`),
  `authz.py` (papéis → permissões, `require_permission`/`require_role`), modelo `User`,
  router `/api/auth`.
- **Frontend** React/TS (Vite), roteamento manual; gate de login + store de sessão +
  injeção de `Authorization` via wrapper global de `fetch` + tratamento de 401/403.
- **Domínios já existentes** (preservados): Central Jurídica, Central de Débitos
  (Etapas A–F), Due Diligence (4 frentes), Checklist Mestre (27 `canonical_key`),
  motor financeiro, Pós-Arrematação, Oportunidade/Workflow (fundação).

## 2. Autenticação e autorização (Onda 11) — entregue

- **Modelo `User`** (migration `0023_usuarios`, aditiva/reversível): `email` único,
  `password_hash` (bcrypt), `name`, `role`, `active`, `last_login_at`. Nenhum
  usuário/senha padrão é criado; o 1º admin é **bootstrap opcional via ambiente**
  (`AUTH_BOOTSTRAP_ADMIN_EMAIL`/`_PASSWORD`), idempotente.
- **Hashing + JWT** (`auth.py`): bcrypt (senha mínima 8); JWT HS256 assinado com
  `JWT_SECRET_KEY` (falha-fechada 503 sem segredo), expiração configurável
  (`ACCESS_TOKEN_EXPIRE_MINUTES`, default 8h). `get_current_user` lê `Authorization:
  Bearer`. Auditoria de login (sucesso/falha) sem expor PII (fingerprint do e-mail);
  token nunca logado.
- **Papéis e permissões** (`authz.py`):

  | Permissão | ADMIN | ANALISTA | OPERADOR | CONSULTA |
  |---|:--:|:--:|:--:|:--:|
  | `read` (consultar) | ✔ | ✔ | ✔ | ✔ |
  | `analysis:write` (análises/dívidas/estimativas) | ✔ | ✔ | ✔ | — |
  | `debt:query` (consulta de débito) | ✔ | ✔ | ✔ | — |
  | `admin:parameters` (parâmetros) | ✔ | — | ✔ | — |
  | `admin:write` (municípios/tipos/fontes/cobertura) | ✔ | — | — | — |
  | `user:manage` (gerenciar usuários) | ✔ | — | — | — |

- **Endpoints** `/api/auth`: `POST /login` (e-mail+senha → JWT), `GET /me` (usuário +
  permissões), `GET/POST/PATCH /usuarios` (somente `user:manage`).
- **Proteção**: validada **no backend** (nunca confia no cliente). Endpoints
  administrativos aceitam JWT (papel) **ou** `X-Admin-Token` (compat em desativação
  controlada). Falha-fechada: 401 sem credencial, 403 sem permissão, 503 quando nenhuma
  credencial está configurada.
- **Frontend**: `LoginPage` + gate em `App.tsx` (sem sessão → só login); store de
  sessão (`session.ts`, memória + localStorage); wrapper global de `fetch` injeta
  `Authorization` e, em 401, limpa a sessão e volta ao login; logout no topo.

## 3. Compatibilidade e preservação

- Endpoints abertos do dossiê permanecem abertos (auth é por-endpoint, não global):
  os ~30 arquivos de teste existentes continuam verdes (729 passed).
- `X-Admin-Token`/`authz_role_tokens` preservados como **compat temporária** (papéis
  `admin`→ADMIN, `operador`→OPERADOR). Testes de Etapas A–F intactos.
- Preservação 633 / V1–V9 / `llm_runs` / 27 `canonical_key` / Central Jurídica: a
  migration `0023` é aditiva (só cria `users`), reversível (down_revision `0022`),
  sem backfill; validada em banco descartável.

## 4. Migrations

`0023_usuarios` (aditiva/reversível). Head = `0023`. Próxima livre = `0024`.

## 5. Endpoints (contrato 119 → 123 paths; +4)

`POST /api/auth/login` · `GET /api/auth/me` · `GET|POST /api/auth/usuarios` ·
`PATCH /api/auth/usuarios/{id}`.

## 6. Testes

- Backend `tests/test_auth.py` (14): hashing/verify, senha curta, JWT roundtrip, JWT
  sem segredo (503), login ok/credencial inválida/inativo (401), me sem token (401),
  admin cria/lista usuários, CONSULTA 403, endpoint admin aceita JWT ADMIN / recusa
  CONSULTA (403), compat X-Admin-Token, bootstrap idempotente.
- Frontend `LoginPage.test.tsx` (2): login sucesso + erro 401.

## 7. Configuração de ambiente (auth)

- `JWT_SECRET_KEY` (obrigatório para autenticar; sem ele, login/validação = 503).
- `ACCESS_TOKEN_EXPIRE_MINUTES` (default 480).
- `AUTH_BOOTSTRAP_ADMIN_EMAIL` / `AUTH_BOOTSTRAP_ADMIN_PASSWORD` / `AUTH_BOOTSTRAP_ADMIN_NAME`
  (opcional — cria o 1º admin só se não houver usuários). **Sem defaults em produção.**
- Dependências novas: `PyJWT==2.10.1`, `bcrypt==4.2.1` (`backend/requirements.txt`).

## 8. Instruções de execução

1. `pip install -r backend/requirements.txt` (instala PyJWT + bcrypt).
2. `alembic upgrade head` (chega a `0023`).
3. Definir `JWT_SECRET_KEY` no ambiente; opcionalmente os `AUTH_BOOTSTRAP_ADMIN_*`
   para criar o 1º admin no startup.
4. Subir a API; o frontend exige login antes de qualquer tela.

---

## 9. Auditoria do produto (Fase 0) — matriz de maturidade

Classificação a partir do **código efetivo** e dos testes (não da documentação).

| Módulo | Status | Evidência | Pendência |
|---|---|---|---|
| Autenticação/RBAC (Onda 11) | IMPLEMENTADO E TESTADO | `auth.py`/`authz.py`/`routers/auth.py`/`0023`; `test_auth.py` (14 verdes) | Expor usuários na UI admin; MFA/rotação (evolução) |
| Central de Débitos (A–F) | IMPLEMENTADO E TESTADO | `debts_service`/`coverage_service`/`estimates_service`/`debt_query_service`; testes verdes | Coletores automáticos (dependência externa) |
| Cobertura municipal | IMPLEMENTADO E TESTADO | `municipality_coverage` + UI Cobertura | — |
| Estimativa condominial | IMPLEMENTADO E TESTADO | `estimates_service` (3 cenários, ESTIMADO) | — |
| Parâmetros centralizados | IMPLEMENTADO E TESTADO (parcial no consumo) | `parameters.py` + consumo em `market.py` + snapshot | Consumo em risco/checklist/workflow ainda hardcoded |
| Análise financeira | IMPLEMENTADO E TESTADO | `finance.py`/`build_finance`; E2E 633 | TIR/VPL/payback não implementados (premissas) |
| Due Diligence (4 frentes) | IMPLEMENTADO E TESTADO | `services` + `DueDiligenceSection` | Integrações externas = NAO_CONFIGURADO sem credencial |
| Central Jurídica | IMPLEMENTADO E TESTADO | `legal_central` + testes | — |
| Checklist Mestre (27 keys) | IMPLEMENTADO E TESTADO | `checklist.py` + execuções | Aplicabilidade por modalidade (ver abaixo) |
| Oportunidade/Workflow | IMPLEMENTADO PARCIALMENTE (fundação, não exposto) | `workflow_rules`/`workflow_engine` (Onda 1) | Serviço/endpoints/transições/UI do ciclo de vida |
| Modalidades de leilão | EXISTE CAMPO, NÃO ESTRUTURADO | `Property.modality` (string livre) | Catálogo canônico + regras dinâmicas (Onda 2) — PLAN-WAVE-2 |
| Dashboard operacional | IMPLEMENTADO PARCIALMENTE | `DashboardHub` (hubs reais) | Indicadores por modalidade/fase; visão única da oportunidade |
| Pós-Arrematação | IMPLEMENTADO E TESTADO | `post_auction` + `PostAuctionSection` | — |

### Fluxo ponta-a-ponta (diagnóstico honesto)
`Entrada do imóvel → análise jurídica → due diligence → débitos/despesas → análise
financeira → riscos → checklist → decisão → pós-arrematação` **existe e é utilizável**
por imóvel. As lacunas para "conduzir a oportunidade por um processo" ponta-a-ponta
são: (a) **modalidades** ainda são string livre (Onda 2 não implementada além da
fundação de planejamento); (b) o **workflow** F0–F13 é motor puro **não exposto**
(sem endpoints/UI de transição); (c) o **dashboard** não consolida por fase/modalidade.
Essas três frentes são as pendências reais para o MVP "plataforma de workflow".

---

## 10. Limitações, dependências externas e riscos

- **Modalidades (Onda 2) e ciclo de vida de workflow exposto** não foram implementados
  nesta rodada — são as maiores pendências para o fluxo ponta-a-ponta; a fundação
  (motor + modelos Opportunity) existe e deve ser reutilizada (sem segundo motor).
- **Coletores automáticos de portais**: dependem de viabilidade + termos + autorização
  por município. Só o fluxo manual/assistido está ativo.
- **Integrações externas** (Google Maps, RI Digital, Prefeitura): `NAO_CONFIGURADO`
  sem credencial — comportamento seguro, sem simular consulta.
- **Auth**: sólida para ambiente controlado; evoluções recomendadas (MFA, rotação de
  segredo, refresh token, bloqueio por tentativas) ficam como melhoria. `X-Admin-Token`
  permanece como compat em desativação controlada.

## 11. Git

Branch `main`; migration head `0023`; commits por bloco publicados em `origin/main`
(ver `PROJECT-HISTORY.md`). Working tree limpo após a publicação.

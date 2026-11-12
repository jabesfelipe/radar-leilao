# Central de Débitos/Despesas + Parametrização Administrável — Etapa A (implementação)

> **Status:** IMPLEMENTADO e VALIDADO em banco descartável (pgvector/pg16 efêmero).
> Complementa (não substitui) o plano em `docs/PLAN-CENTRAL-DEBITOS-DESPESAS-ADMIN.md`.
> **Escopo desta etapa:** fundação de dados + serviços + APIs + 1ª UI administrativa.
> **Fora de escopo (NÃO implementado):** coletores/scraping, consulta real a portais,
> agentes LLM da central, modalidades, e as Etapas B–F.

Base de código: branch `main`. Migration de referência: `0020_central_debitos`
(down_revision `0019_opportunity_fk`).

---

## 1. Princípios aplicados

- **Aditivo e não-destrutivo.** `Debt`/`Cost` e todos os seus endpoints permanecem
  intactos. O novo domínio normalizado coexiste; nada é migrado/backfillado (Gate 2
  não autorizado).
- **CONFIRMADO ≠ ESTIMADO ≠ INFORMADO.** A confiabilidade e o status são campos de
  primeira classe; um valor `ESTIMADO` nunca é promovido a `OFICIAL`/`CONFIRMADO`
  automaticamente (reforçado em `normalize_debt_payload`).
- **Ausência de resultado ≠ ausência de débito.** A consolidação separa o passivo
  apurado do que está "não apurado", sem assumir zero.
- **Parâmetros de negócio administráveis, versionados e transversais.** O catálogo de
  parâmetros não é exclusivo de débitos; serve a todo o produto, com resolução por
  precedência e histórico imutável.
- **Falha-fechada na administração.** Escrita administrativa exige token; sem token
  configurado, a escrita é recusada (503). Proteção **provisória** até RBAC (Onda 11).

---

## 2. Modelo de domínio (6 tabelas novas)

Todas criadas pela migration `0020_central_debitos` (aditiva/reversível).

| Tabela | Papel |
|---|---|
| `municipalities` | Municípios cadastráveis + flag de cobertura. Únicos: `ibge_code` e (`name`,`state`). |
| `debt_types` | Catálogo administrável de tipos de débito/despesa. `code` único; `group`, `default_nature`, `canonical_cost_key`, `impacts_finance`. |
| `debt_sources` | Fontes por município×categoria. **Apenas cadastro** (sem consulta externa). Situação, requisitos de acesso, limitações, URL oficial. |
| `property_debts` | Débito/despesa **normalizado** por imóvel/oportunidade. Rico: natureza, status, confiabilidade, valores (original/juros/multa/correção/atualizado), datas, origem, evidência. |
| `parameters` | Catálogo **central** de parâmetros (transversal). Escopo, tipo de dado, valor/default, limites, vigência, versão, status. |
| `parameter_history` | Trilha **imutável** de alterações de parâmetro (versão, antes/depois, ator, justificativa). |

Pontos de integridade:
- `property_debts.opportunity_id` é **NULLABLE** (Gate 1; NULL = legado).
- `property_debts` referencia `properties`, `opportunities`, `municipalities`,
  `debt_sources` e `evidences` (todos opcionais exceto `property_id`).
- `parameters` tem unicidade composta `(key, scope, municipality_id, debt_category)`
  — permite múltiplas versões de escopo distintas sob a mesma chave lógica.

### Enums/vocabulários (em `backend/app/models.py`)

- `DEBT_GROUPS`, `DEBT_NATURES`, `DEBT_STATUSES`, `DEBT_RELIABILITIES`,
  `DEBT_SOURCE_TYPES`.
- `PARAMETER_DATA_TYPES` (STRING/INTEGER/DECIMAL/BOOLEAN/JSON),
  `PARAMETER_SCOPES` (GLOBAL/MUNICIPIO/CATEGORIA/MUNICIPIO_CATEGORIA),
  `PARAMETER_STATUSES`.

---

## 3. Serviços de domínio

### 3.1 Parâmetros (`backend/app/parameters.py`)

- `coerce_value` / `serialize_value`: conversão tipada conforme `data_type`, com
  validação de `allowed_values`, `min_value`/`max_value`. Erros viram `ParameterError`.
- `create_parameter` / `update_parameter`: toda escrita incrementa `version` e grava
  uma linha **imutável** em `parameter_history` (antes/depois/ator/justificativa).
- `resolve` / `resolve_detail`: resolução por **precedência**, do mais específico ao
  mais genérico:

  `MUNICIPIO_CATEGORIA` → `MUNICIPIO` → `CATEGORIA` → `GLOBAL` → `default_value` → default do chamador

  `resolve_detail` retorna também a origem (qual escopo venceu), útil para auditoria/UI.

### 3.2 Central de débitos/despesas (`backend/app/debts_service.py`)

- `DEBT_TYPE_SEED` (20 tipos) e `MUNICIPALITY_SEED` (4 municípios com código IBGE:
  Curitiba 4106902, São José dos Pinhais 4125506, Fazenda Rio Grande 4107652,
  Assis 3504008). Seeds **idempotentes** (`seed_debt_types`, `seed_municipalities`,
  `seed_all`).
- `normalize_debt_payload`: valida e normaliza o payload manual — aplica a natureza
  default do tipo quando ausente, garante vocabulário válido e o invariante
  **ESTIMADO nunca vira OFICIAL/CONFIRMADO**.
- `consolidate`: leitura pura que agrega por natureza (confirmados, informados,
  estimados, despesas previstas, não apurados). Usa o valor **atualizado quando
  houver, senão o original** (sem dupla contagem) e inclui o legado `Debt` na visão,
  sem alterar o consumo atual de `build_finance`.

### 3.3 Integração com o financeiro

`finance.build_finance` **não foi alterado**. A consolidação da central é leitura e
convive com o cálculo atual (que segue consumindo `Debt`), sem dupla contagem. A
compatibilidade está coberta por teste (`tests/test_central_debitos.py`).

---

## 4. Contratos de API

Montados em `backend/app/main.py` via `include_router` (admin + debitos).

### 4.1 Administração — `backend/app/routers/admin.py` (prefix `/api/admin`)

Leitura **aberta**; escrita **protegida** por `require_admin` (header `X-Admin-Token`
== `settings.admin_api_token`; sem token configurado → 503; token errado/ausente → 401).

| Método | Caminho | Proteção |
|---|---|---|
| GET  | `/api/admin/municipios` | aberto (semeia on-read) |
| POST | `/api/admin/municipios` | admin |
| PATCH| `/api/admin/municipios/{id}` | admin |
| GET  | `/api/admin/tipos-debito` | aberto (semeia on-read) |
| POST | `/api/admin/tipos-debito` | admin |
| PATCH| `/api/admin/tipos-debito/{id}` | admin |
| GET  | `/api/admin/fontes` | aberto (filtros `municipality_id`, `debt_category`) |
| POST | `/api/admin/fontes` | admin |
| PATCH| `/api/admin/fontes/{id}` | admin |
| GET  | `/api/admin/parametros` | aberto (filtros `category`, `key`) |
| GET  | `/api/admin/parametros/categorias` | aberto |
| GET  | `/api/admin/parametros/resolver` | aberto (`key`, `municipality_id?`, `debt_category?`) |
| GET  | `/api/admin/parametros/{id}/historico` | aberto |
| POST | `/api/admin/parametros` | admin |
| PATCH| `/api/admin/parametros/{id}` | admin |

### 4.2 Central de débitos por imóvel — `backend/app/routers/debts.py`

Reusa `property_or_404`, `record_event`, `record_history`, `serialize`. Não há
consulta externa — o registro é manual.

| Método | Caminho |
|---|---|
| GET  | `/api/imoveis/{id}/debitos` (lista normalizada + legado + consolidação) |
| GET  | `/api/imoveis/{id}/debitos/consolidacao` |
| GET  | `/api/imoveis/{id}/debitos/{debt_id}` |
| POST | `/api/imoveis/{id}/debitos` (registro manual; gera evento + histórico) |
| PATCH| `/api/imoveis/{id}/debitos/{debt_id}` (revalida invariantes de natureza/status) |

Contrato OpenAPI: **113 paths** (eram 99; +14 adições intencionais). Baseline
regenerado em `tests/contract/openapi_baseline.json`.

---

## 5. Segurança e dependência de RBAC

A escrita administrativa é protegida por `X-Admin-Token` == `settings.admin_api_token`
(novo campo em `backend/app/config.py`, default `None` = falha-fechada). Isso **não é**
autenticação real nem substitui RBAC: é uma barreira provisória, deliberada e
documentada, reusando o padrão já existente do reveal de credencial.

**Dependência registrada:** a área administrativa só deve ser exposta em produção após
a frente de **auth/RBAC (Onda 11)**. Até lá, `ADMIN_API_TOKEN` deve ser configurado via
ambiente (nunca hardcoded) e a UI admin tratada como ferramenta interna.

---

## 6. Frontend (1ª UI administrativa)

- `frontend/src/services/admin.ts`: cliente das rotas `/api/admin` (envia
  `X-Admin-Token` nas escritas).
- `frontend/src/pages/AdminPage.tsx`: abas `overview`/`municipios`/`fontes`/`tipos`/
  `parametros` — listagens reais, cadastro, edição de parâmetro (nova versão) e
  histórico. O token é digitado na própria tela (não persistido). Usa os componentes de
  design existentes (`Alert` com `tone`, `Badge` com `tone`).
- Navegação: item **Administração** no `Sidebar.tsx` e rota `/administracao` no
  `App.tsx` (HubRouter). Estilos em `styles.css` (`.admin-*`).
- Teste: `frontend/src/pages/AdminPage.test.tsx`.

---

## 7. Compatibilidade e preservação

- `Debt`/`Cost` e endpoints legados **intactos**; `build_finance` inalterado.
- Nenhum backfill; `opportunity_id` legado permanece NULL.
- Preservação de imóvel 633 / V1–V9 / `llm_runs` / 27 `canonical_key` / Central
  Jurídica respeitada — validação feita apenas em PostgreSQL efêmero.

---

## 8. Validação (banco descartável)

- **Backend:** 682 passed / 2 skipped (RC=0), incluindo os novos
  `tests/test_parameters.py` e `tests/test_central_debitos.py`.
- **Migrations:** `upgrade head` (até `0020`), `downgrade 0019` e `re-upgrade` — todos RC=0.
- **Frontend:** `tsc -b` OK + 141 passed / 23 arquivos.
- **Contrato:** `openapi_baseline.json` = 113 paths (adições intencionais).

---

## 9. Débitos técnicos e pendências

- **RBAC real** (Onda 11) é bloqueante para expor a admin em produção; o token é
  provisório.
- **Despesas realizadas**: Etapa A reusa `Cost`/`PostAuctionCost` existentes; não há
  tabela nova de despesa (decisão para evitar duplicação).
- **Coletores/consulta real/agentes/modalidades** permanecem fora de escopo (Etapas B–F).
- A Onda 2 (modalidade) deverá usar a próxima migration livre (`0021`).

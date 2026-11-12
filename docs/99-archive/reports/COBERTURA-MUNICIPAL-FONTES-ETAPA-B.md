# Cobertura municipal e fontes de consulta — Etapa B (implementação)

> **Status:** IMPLEMENTADO e VALIDADO em banco descartável (pgvector/pg16 efêmero).
> Complementa a Etapa A (`CENTRAL-DEBITOS-DESPESAS-ADMIN-ETAPA-A.md`) e o plano
> (`PLAN-CENTRAL-DEBITOS-DESPESAS-ADMIN.md`).
> **Escopo desta etapa:** matriz operacional de cobertura município × tipo de débito +
> cadastro/edição de fontes + 1ª visão administrativa de cobertura + inventário
> documental das fontes oficiais + especificação da arquitetura de adaptadores.
> **Fora de escopo (NÃO implementado):** coletores/scraping, consulta real a portais,
> integrações externas, agentes LLM, modalidades, Etapas C–F.

Base de código: branch `main`. Migration de referência: `0021_cobertura_municipal`
(down_revision `0020_central_debitos`).

---

## 1. O que a Etapa B entrega

A Etapa A deixou a cobertura como um **flag global** por município
(`Municipality.coverage_active`) e a ligação com fontes era frouxa
(`DebtSource.debt_category`, string). A Etapa B introduz a **matriz operacional de
cobertura por município × tipo de débito**, independente por combinação e vivendo como
**dado administrável** — nunca em condicionais fixas no código.

Princípios honestos reforçados:
- **Cobertura independente por município e por tipo.** Curitiba pode cobrir IPTU com um
  nível e deixar dívida ativa como não investigada; outro município, outro arranjo.
- **Ausência de investigação ≠ ausência de débito.** O estado inicial honesto é
  `NAO_INVESTIGADA`; a matriz expõe explicitamente as combinações ainda não investigadas.
- **Nenhuma automação sem autorização.** As fontes são apenas cadastradas; nenhuma
  consulta real, scraping ou integração foi executada.

---

## 2. Modelo de dados (tabela nova)

Migration `0021_cobertura_municipal` (aditiva, reversível). Tabela
**`municipality_coverage`** (município × tipo de débito):

| Coluna | Papel |
|---|---|
| `municipality_id` (FK) | município coberto |
| `debt_type_code` | `code` de `DebtType` |
| `level` | nível de cobertura (`COVERAGE_LEVELS`) |
| `situation` | situação operacional da fonte (`DEBT_SOURCE_SITUATIONS`) |
| `method` | método de consulta (`DEBT_CONSULTATION_METHODS`) |
| `active` | cobertura ligada/desligada |
| `source_id` (FK, opcional) | fonte preferencial (mesmo município) |
| `identifier_required` | identificador exigido (ex.: Inscrição Imobiliária) |
| `limitations`, `observations` | texto livre |
| `last_validated_at` | data da última validação registrada pelo operador |

Unicidade `(municipality_id, debt_type_code)` — uma linha por combinação, sem
duplicidade. A tabela é **folha** (drop simples no downgrade); não toca Etapa A.

### Vocabulários canônicos (em `backend/app/models.py`)

- `COVERAGE_LEVELS`: `NAO_INVESTIGADA` · `MANUAL` · `PARCIAL` · `AUTOMATIZAVEL` ·
  `INTEGRACAO_DISPONIVEL` · `INDISPONIVEL`.
- `DEBT_SOURCE_SITUATIONS`: `NAO_INVESTIGADA` · `EM_INVESTIGACAO` · `DISPONIVEL` ·
  `INDISPONIVEL` · `DEPENDE_AUTENTICACAO` · `BLOQUEADA`.
- `DEBT_CONSULTATION_METHODS`: `MANUAL` · `PORTAL_PUBLICO` · `SERVICO_OFICIAL` ·
  `API_OFICIAL` · `DOCUMENTO` · `INDEFINIDO`.

---

## 3. Serviço de cobertura (`backend/app/coverage_service.py`)

- `COVERAGE_SEED`: cobertura **inicial como dado** para os 4 municípios. Honesta: só o
  **IPTU** tem portal público identificado (`level=AUTOMATIZAVEL`,
  `method=PORTAL_PUBLICO`); dívida ativa e taxas entram como `NAO_INVESTIGADA`/`MANUAL`.
- `seed_coverage`: idempotente (não recria, não sobrescreve edições do operador);
  integrado em `debts_service.seed_all` (semeado on-read nos GETs).
- `create_coverage` / `update_coverage`: validam referências (município/tipo existentes,
  fonte do mesmo município), vocabulário e **recusam duplicidade**. `mark_validated`
  carimba `last_validated_at`.
- `coverage_matrix`: leitura pura — lista as coberturas + os tipos ativos ainda **não
  investigados** por município (ausência visível) + uma **ressalva** explícita.

---

## 4. APIs (admin)

Novos endpoints em `backend/app/routers/admin.py` (prefixo `/api/admin`). Leitura
aberta; escrita protegida por `require_admin` (`X-Admin-Token`, falha-fechada —
**provisório até RBAC Onda 11**).

| Método | Caminho | Proteção |
|---|---|---|
| GET  | `/api/admin/cobertura` (matriz; semeia on-read; filtro `municipality_id`) | aberto |
| POST | `/api/admin/cobertura` | admin |
| PATCH| `/api/admin/cobertura/{id}` (nível/situação/ativo/validação) | admin |

Fontes evoluídas (Etapa A → B): `create_source`/`update_source` agora **validam** a
`debt_category` contra o catálogo de tipos e o vocabulário de `source_type`/`situation`
(400/422). O cadastro de fontes passou a ser efetivamente usado pela UI.

Contrato OpenAPI: **115 paths** (eram 113; +2 intencionais). Baseline regenerado em
`tests/contract/openapi_baseline.json`.

---

## 5. Frontend (UI administrativa)

- `frontend/src/services/admin.ts`: tipos `Coverage`/`CoverageMatrix`; `updateSource`;
  `listCoverage`/`createCoverage`/`updateCoverage`.
- `frontend/src/pages/AdminPage.tsx`:
  - Nova aba **Cobertura**: matriz município × tipo com `Badge` de nível, **ativar/
    desativar**, **marcar validação**, tabela de **cobertura não investigada** (com ação
    "marcar em investigação") e formulário de nova cobertura.
  - Aba **Fontes** reescrita: agora com **formulário de cadastro e edição** (antes era
    somente leitura), com selects de tipo de fonte e situação.
  - Visão geral com contadores de cobertura mapeada e não investigada.

---

## 6. Inventário das fontes oficiais (documental)

Levantamento de **existência de portais públicos** (web search; **nenhuma consulta de
débito real** foi feita, nenhum CAPTCHA/autenticação contornado). "API oficial
documentada" **não** foi confirmada para nenhum município.

| Município | Portal identificado | Órgão | Identificador | Classificação (IPTU) |
|---|---|---|---|---|
| **Curitiba/PR** | `iptu-dam.curitiba.pr.gov.br`, `financas.curitiba.pr.gov.br` | Sec. de Finanças (rendas imobiliárias) | Inscrição Imobiliária + Sublote **ou** Indicação Fiscal | Portal público de consulta (potencialmente automatizável) |
| **São José dos Pinhais/PR** | `sjp.pr.gov.br/.../iptu`, `financas.sjp.pr.gov.br` | Semfi | Inscrição/cadastro imobiliário (a confirmar) | Portal de finanças (consulta IPTU/Taxa de Lixo) |
| **Fazenda Rio Grande/PR** | `fazendariogrande.pr.gov.br` | Divisão de Arrecadação | A investigar | Portal (2ª via IPTU); possível `atende.net` (não confirmado) |
| **Assis/SP** | `tributacao.assis.sp.gov.br` | Sistema de Arrecadação | Cadastro do imóvel (a confirmar) | Portal de arrecadação (**NÃO** confundir com a capital SP) |

Para **todos**: dívida ativa, certidões e API oficial = `NAO_INVESTIGADA`. Automação de
portal só entraria por município, condicionada a termos de uso e autorização (Etapas E/F).

---

## 7. Arquitetura de adaptadores (especificação)

A especificação do contrato `MunicipalDebtProvider` e da camada de coletores
(entrada/saída normalizada, indisponibilidade, timeout/retry/rate-limit/circuit-breaker,
evidências, logs, status da consulta) está em
`docs/SPEC-ADAPTADORES-CONSULTA-MUNICIPAL.md`. **Nenhum adaptador/coletor foi
implementado** — é apenas o contrato que provedores futuros deverão cumprir, mantendo o
domínio independente de portais.

---

## 8. Compatibilidade e preservação

- `Debt`/`Cost`/`PropertyDebt`, evidências, endpoints, motor financeiro e parâmetros
  **intactos**. Sem backfill. Central Jurídica não tocada.
- Preservação de imóvel 633 / V1–V9 / `llm_runs` / 27 `canonical_key` respeitada —
  validação apenas em PostgreSQL efêmero.

---

## 9. Validação (banco descartável)

- **Backend:** 694 passed / 2 skipped (RC=0; +12 testes em `tests/test_cobertura_municipal.py`).
- **Migrations:** `upgrade head` (até `0021`), `downgrade 0020` e `re-upgrade` — todos RC=0.
- **Frontend:** `tsc -b` OK + 143 passed / 23 arquivos.
- **Contrato:** `openapi_baseline.json` = 115 paths (adições intencionais).

---

## 10. Débitos técnicos e pendências

- **RBAC real** (Onda 11) continua bloqueante para expor a admin em produção; token
  provisório.
- **Coletores/consulta real/agentes/modalidades** permanecem fora de escopo (Etapas C–F).
- A tabela `debt_query` (execução por consulta) só será criada quando a orquestração de
  coleta for autorizada (Etapa E).
- A próxima migration livre é `0022`.

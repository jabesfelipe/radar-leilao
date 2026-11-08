# Central de Débitos, Despesas e Automação — Etapas C–F (relatório consolidado)

> **Status:** IMPLEMENTADO e VALIDADO em banco descartável (pgvector/pg16 efêmero).
> Continuação das Etapas A (fundação) e B (cobertura). Complementa
> `PLAN-CENTRAL-DEBITOS-DESPESAS-ADMIN.md`, `CENTRAL-DEBITOS-DESPESAS-ADMIN-ETAPA-A.md`,
> `COBERTURA-MUNICIPAL-FONTES-ETAPA-B.md` e `SPEC-ADAPTADORES-CONSULTA-MUNICIPAL.md`.
>
> **Entregue nesta rodada (C–F + segurança):** estimativa condominial parametrizada;
> consumo real de parâmetros centralizados nos serviços + snapshot por execução;
> contrato e provider de consulta municipal (manual/assistido) com persistência e
> histórico; integração da consolidação de débitos ao dossiê do imóvel; e uma camada
> de autorização por papel/permissão sobre o token administrativo.
>
> **NÃO entregue (dependência externa, deliberado):** coletores/adaptadores automáticos
> de portais reais (dependem de viabilidade + termos de uso + autorização), identidade
> de usuários (login/sessão/JWT — Onda 11). Ver §8.

Base: branch `main`. Migration de referência: `0022_consulta_estimativa`
(down_revision `0021_cobertura_municipal`). Alembic head = `0022`.

---

## 1. Arquitetura final (visão)

```
Catálogo de parâmetros (Parameter) ──resolve()/resolve_detail()──> serviços
     │                                                              │
     ├─ market.py (amostra mínima, CV dispersão)                    │
     ├─ estimates_service.py (condomínio: cenários + alertas)       │
     └─ parameter_snapshot() ──> FinancialAnalysis.inputs (imutável por execução)

Consulta municipal:
  routers/debts.py ─> debt_query_service.run_query()
        ├─ debt_providers.select_provider(cobertura município×tipo)
        │       └─ ManualAssistedProvider (fallback sempre válido)
        ├─ debts_service.normalize_debt_payload() ──> PropertyDebt (reuso)
        ├─ DebtQuery (execução: status/provider/tentativas/mensagem)
        └─ reflect_due_diligence_signals() ──> frente PREFEITURA / checklist

Consolidação (leitura): debts_service.consolidate() ──> dossiê (DebtsSection) + build_finance intacto

Autorização: authz.require_permission(perm) sobre X-Admin-Token (papéis admin/operador)
```

Princípios preservados: determinístico (LLM nunca inventa valor); `CONFIRMADO ≠ ESTIMADO
≠ INFORMADO`; ausência de resultado ≠ ausência de débito; parâmetros versionados com
snapshot por execução (análises passadas imutáveis); sem dupla contagem no financeiro.

---

## 2. Etapa C — Condomínio e estimativa de despesas

- **Serviço** `backend/app/estimates_service.py`:
  - `compute_condominium_estimate`: 3 cenários (conservador/provável/otimista),
    memória de cálculo, grau de confiança; **sempre `status=ESTIMADO`,
    `nature=ESTIMATIVA_OPERACIONAL`** (nunca passivo confirmado).
  - Separação rigorosa: **idade do imóvel ≠ idade do condomínio ≠ tempo de
    financiamento ≠ período de inadimplência**. A inadimplência é parâmetro explícito
    (`condominio.periodo_presumido_meses`), **nunca derivada da idade**.
  - `age_alerts`: alertas de idade **parametrizáveis** que respeitam a qualidade da
    informação — idade desconhecida/estimada ⇒ alerta **não conclusivo**.
- **Persistência** (`CondominiumEstimate`): snapshot imutável do cálculo + parâmetros
  usados (`assumptions` JSON). Não altera estimativas anteriores.
- **Endpoints**: `POST /api/imoveis/{id}/debitos/estimar-condominio` (calcula + opcional
  persiste) e `GET …/debitos/estimativas-condominio`.

## 3. Etapa D — Parâmetros centralizados (consumo real + snapshot)

- **Catálogo** (`parameter_seeds.py`, idempotente): `mercado.amostra_minima`,
  `mercado.cv_dispersao_alta`, `condominio.periodo_presumido_meses`,
  `condominio.margem_seguranca_pct`, `condominio.fator_otimista`,
  `checklist.idade_alerta_1_anos`, `checklist.idade_alerta_2_anos`.
- **Consumo efetivo** (não apenas cadastro):
  - `market.py` deixou de usar `MIN_SAMPLE`/`HIGH_DISPERSION_CV` hardcoded; o router
    `routers/market.py` resolve via `parameters.resolve` e injeta (defaults = valores
    históricos, preservando compatibilidade).
  - `estimates_service.py` resolve os parâmetros de condomínio/alertas.
- **Precedência** preservada: `MUNICIPIO_CATEGORIA > MUNICIPIO > CATEGORIA > GLOBAL >
  default_value > default`. Verificado por teste (override por município).
- **Snapshot por execução** (`parameters.parameter_snapshot`): a análise financeira
  grava os parâmetros resolvidos em `FinancialAnalysis.inputs.parametros` — **uma
  alteração administrativa futura não muda análises passadas** (invariante que preserva
  V1–V9). Constantes técnicas, segredos e fiscais sem fonte **não** viraram parâmetros.

## 4. Etapa E — Consulta e coleta municipal (contrato + manual/assistido)

- **Contrato** `MunicipalDebtProvider` (`debt_providers.py`): `DebtQueryContext` (entrada)
  → `DebtQueryResult` (saída normalizada) com status padronizados
  (`DEBT_QUERY_STATUSES`). Registry com **seleção por dado** (cobertura município×tipo),
  nunca condicional fixa de cidade.
- **Provider `ManualAssistedProvider`** (fallback sempre válido): estrutura/valida os
  valores informados pelo operador a partir da fonte oficial; distingue
  `REQUER_INTERVENCAO_MANUAL` / `SEM_OCORRENCIA` / `CONCLUIDA`. **Nenhum acesso a portal,
  scraping ou contorno de CAPTCHA/autenticação.**
- **Orquestração** `debt_query_service.run_query`: seleção de provider, **retry
  controlado** (só status transitório `INDISPONIVEL`/`ERRO`, limite 1–5), timeout/log,
  persistência da execução (`DebtQuery`) + resultado normalizado (`PropertyDebt`
  reusado) + evento/histórico. Reflete pendência na frente PREFEITURA.
- **Endpoints**: `POST /api/imoveis/{id}/debitos/consultar`, `GET …/debitos/consultas`.
- **Classificação de fonte** permanece em `debt_sources`/cobertura (Etapas A/B): API
  oficial / serviço oficial / portal / não investigada. Nenhum provider automático real
  foi implementado (Etapa futura, condicionada a viabilidade + autorização).

## 5. Etapa F — Integração à análise do imóvel

- **Dossiê**: nova seção **Débitos e despesas** (`DebtsSection.tsx`) no detalhe do
  imóvel, com consolidação por natureza (confirmado/informado/estimado/despesa
  prevista/não apurado), exposição de passivo **com ressalva**, histórico de consultas e
  estimativa condominial — integrada ao backend real.
- **Financeiro**: `build_finance` **não** foi alterado (continua consumindo `Debt` em
  `custos.debitos`); a consolidação rica da Central é leitura paralela, **sem dupla
  contagem** (valor atualizado quando houver, senão original; estimativa nunca entra
  como passivo confirmado). Verificado por teste.
- **Due diligence**: a consulta reflete pendência na frente PREFEITURA e no item de
  checklist `RESPONSABILIDADE_DEBITOS` (reuso do padrão existente), sem nova versão de
  análise e sem conclusão automática.

## 6. Segurança — autorização por papel (sobre o token)

- `authz.py`: permissões granulares (`admin:write`, `admin:parameters`, `debt:query`),
  papéis (`admin` = tudo; `operador` = parâmetros + consulta), `require_permission(perm)`
  validado **no backend**. Falha-fechada: **503** sem token configurado, **401** token
  ausente/inválido, **403** papel sem permissão. O token nunca é exposto em logs/respostas.
- Mapeamento papel→token: `admin` = `settings.admin_api_token`; papéis adicionais via
  `settings.authz_role_tokens` (JSON, por ambiente) — sem recompilar.
- **Dependência registrada (não resolvida):** identidade de usuários (login/sessão/JWT)
  e RBAC completo são da **Onda 11**. Até lá, a credencial é o token e o papel deriva
  dele. Isto **não** é segurança definitiva para produção — documentado e assumido.

---

## 7. Endpoints (contrato OpenAPI 115 → 119 paths; +4)

| Método | Caminho | Observação |
|---|---|---|
| POST | `/api/imoveis/{id}/debitos/consultar` | consulta via provider (manual/assistido) |
| GET  | `/api/imoveis/{id}/debitos/consultas` | histórico de consultas |
| POST | `/api/imoveis/{id}/debitos/estimar-condominio` | estimativa (3 cenários, ESTIMADO) |
| GET  | `/api/imoveis/{id}/debitos/estimativas-condominio` | estimativas persistidas |

Endpoints de cobertura/parâmetros/fontes da Etapa B agora sob autorização por papel.

## 8. Modelos e migrations

- Migration `0022_consulta_estimativa` (aditiva/reversível): tabelas `debt_queries`
  (execução de consulta) e `condominium_estimates` (estimativa parametrizada). `0001`
  atualizada (`TABLES_ADDED_LATER`). Reversibilidade validada: `upgrade head` →
  `downgrade 0021` → `re-upgrade`, todos RC=0.

## 9. Testes executados

- **Backend (banco descartável):** suíte completa verde (ver cabeçalho do STATUS para o
  número exato) + `tests/test_etapas_cf.py` (parâmetros/precedência/snapshot, estimativa
  3 cenários + idade≠inadimplência, provider manual/sem-ocorrência/assistido/retry,
  consolidação sem dupla contagem, autorização 503/401/403/ok, HTTP estimativa/consulta).
- **Frontend:** `tsc -b` limpo + **146 passed / 24 arquivos** (inclui `DebtsSection.test.tsx`).
- **Migrations:** up/down(0021)/up RC=0. **Contrato:** 119 paths (baseline regenerado).

## 10. Fontes municipais e nível de validação (inalterado desde a Etapa B)

Curitiba/PR, São José dos Pinhais/PR, Fazenda Rio Grande/PR e Assis/SP: apenas IPTU tem
portal público identificado (`AUTOMATIZAVEL`/portal, **não** automatizado); dívida ativa,
taxas e certidões = `NAO_INVESTIGADA`. Nenhuma API oficial confirmada. Nenhuma consulta
de débito real foi executada.

## 11. Providers implementados

- `ManualAssistedProvider` (determinístico, sem rede) — fallback sempre válido.
- **Nenhum provider automático de portal** foi implementado (dependência externa).

## 12. Limitações externas e riscos remanescentes

- **Identidade/RBAC real (Onda 11):** bloqueante para expor a admin em produção. O token
  é provisório.
- **Coletores automáticos:** dependem de viabilidade técnica + termos de uso +
  autorização por município; só então um provider automático é registrado no registry.
- **Parâmetros fiscais (ITBI/emolumentos):** deliberadamente fora do seed — só entram com
  fonte oficial + vigência.
- **Instabilidade do Docker no ambiente de validação:** o PostgreSQL efêmero apresentou
  reinícios intermitentes; os resultados verdes foram obtidos em execuções estáveis e por
  execução dirigida dos módulos novos.

## 13. Instruções de operação

- **Configurar o token admin:** `ADMIN_API_TOKEN=<segredo>` no ambiente (nunca
  versionar). Papéis adicionais: `AUTHZ_ROLE_TOKENS='{"operador":"<token>"}'`.
- **Parâmetros:** administrar em `/administracao` (aba Parâmetros). Alterações geram nova
  versão + histórico; análises passadas preservam o snapshot.
- **Cobertura/fontes:** aba Cobertura/Fontes (escrita exige papel `admin`).
- **Consulta/estimativa por imóvel:** dossiê → aba **Débitos e despesas**.
- **Migrations:** `alembic upgrade head` (chega a `0022`). Reversível até `0021`.

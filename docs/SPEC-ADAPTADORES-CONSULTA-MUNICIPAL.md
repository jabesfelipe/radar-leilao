# Especificação — Arquitetura de adaptadores de consulta municipal (Etapa B)

> **Status:** ESPECIFICAÇÃO (design). **Nenhum coletor/adaptador foi implementado**
> nesta etapa. Nenhuma consulta real a portais, scraping, automação ou integração
> externa foi executada. Este documento define o **contrato** a ser cumprido por
> provedores futuros, para que o domínio permaneça independente de portais.
>
> A Etapa B entrega a **matriz de cobertura** (município × tipo de débito) e o
> cadastro de fontes; a implementação de adaptadores concretos é das Etapas E/F,
> condicionada a viabilidade técnica, termos de uso e autorização explícita.

Base: branch `main`. Complementa `PLAN-CENTRAL-DEBITOS-DESPESAS-ADMIN.md` (§8/§9) e
`CENTRAL-DEBITOS-DESPESAS-ADMIN-ETAPA-A.md`.

---

## 1. Princípios

- **O núcleo não conhece portais.** Toda especificidade de município/portal fica
  confinada a um adaptador. O domínio fala apenas com o contrato (porta).
- **Determinístico, não LLM.** Coleta, identificação e cálculo de valores são
  determinísticos — adaptadores/serviços/workers, nunca "um agente LLM por município".
  LLM só interpreta documento não estruturado já obtido (reusa `extraction.py`), com
  evidência, e nunca inventa/declara valor.
- **Fallback manual sempre válido.** A ausência de adaptador (ou sua indisponibilidade)
  nunca derruba a apuração: o registro manual assistido (Etapa A) permanece.
- **Ausência de resultado ≠ ausência de débito.** Um resultado vazio é um estado
  explícito (`SEM_OCORRENCIA`/`INDISPONIVEL`), não "zero débitos".
- **Nada sem autorização.** CAPTCHA/autenticação nunca são contornados; automação de
  portal só com termos de uso compatíveis e autorização.

---

## 2. Contrato do provedor (porta)

Nome alinhado ao padrão do projeto (`judicial_client`, `geocoding_client`):
**`MunicipalDebtProvider`**. Cada município × tipo (ou família de tipos) implementa este
contrato num adaptador isolado, testável e substituível.

```
class MunicipalDebtProvider(Protocol):
    name: str                 # identificador do adaptador (ex.: "curitiba_iptu_dam")
    municipality_ibge: str    # a quem atende
    debt_types: tuple[str]    # codes de DebtType cobertos
    version: str              # versionamento do adaptador

    def consultar(self, ctx: DebtQueryContext) -> DebtQueryResult: ...
```

A resolução de qual provedor usar parte da **matriz de cobertura** (tabela
`municipality_coverage`): só combinações com `level` integrável e `active=True` têm
provedor; as demais caem no fallback manual.

### 2.1 Entrada — `DebtQueryContext`
- `property_id`, `opportunity_id` (opcional), `municipality_id`.
- `debt_type_code`.
- `identifiers`: dict com o(s) identificador(es) exigido(s) pela fonte (ex.: Inscrição
  Imobiliária + Sublote, Indicação Fiscal, cadastro do imóvel) — ver coluna
  `municipality_coverage.identifier_required`.
- `reference_date` (data-base desejada da apuração).
- `credentials_ref`: **referência** a credencial no cofre (`secrets_crypto`), nunca o
  segredo em claro.

### 2.2 Saída normalizada — `DebtQueryResult`
Resultado heterogêneo do portal normalizado no modelo comum, pronto para virar
`PropertyDebt` (Etapa A) sem perda de rastreabilidade:
- `status`: ver §4 (status da consulta).
- `items`: lista de lançamentos normalizados, cada um com os campos de `PropertyDebt`
  (natureza, `original_amount`/`updated_amount` separados, competência, vencimento,
  `reliability`, etc.). **Estimativa nunca é marcada como OFICIAL.**
- `evidence`: payload bruto + metadados para gravar via `Evidence`/`EvidenceLink`.
- `source_id`: fonte (`debt_sources`) efetivamente usada.
- `queried_at`, `provider_version`.
- `messages`: avisos/limitações estruturados (ex.: "dívida ativa não coberta").

O serviço que persiste o resultado reusa `normalize_debt_payload` (invariantes de
natureza/status/confiabilidade) e grava evento/histórico (`record_event`/`record_history`).

---

## 3. Resiliência (requisitos de cada adaptador)

Cada adaptador concreto DEVERÁ implementar, de forma isolada do domínio:

- **Timeout** por requisição (configurável via catálogo de parâmetros — categoria
  operacional; sem número mágico no código).
- **Retry** controlado com backoff, apenas para falhas transitórias (nunca para 4xx
  de autenticação/autorização).
- **Rate limit** por fonte (respeitar limites do portal; nunca martelar).
- **Tratamento de indisponibilidade:** falha vira `INDISPONIVEL`/`ERRO`, nunca exceção
  vazando para o domínio; a apuração segue com fallback manual.
- **Circuit breaker** por fonte (opcional, Etapa E): abrir após N falhas, meia-abertura
  programada.
- **Logs estruturados** (sem PII sensível em claro; sem segredo) com `provider`,
  `municipality`, `debt_type`, `status`, `duration_ms`, `attempt`.
- **Evidência** de cada consulta (sucesso ou falha) via `Evidence`.
- **Fixtures de resposta simulada** para testes — **nunca** chamar o portal real em teste.

Credenciais sempre via `secrets_crypto` (Fernet, falha-fechada); o adaptador recebe uma
referência, resolve sob demanda e nunca loga o valor.

---

## 4. Status da consulta (vocabulário proposto)

Alinhado ao padrão de `due_diligence_fronts`. Será materializado em uma tabela
`debt_query` (execução por consulta) **em etapa futura** — não criada na Etapa B:

`PENDENTE` · `EM_EXECUCAO` · `CONCLUIDA` · `PARCIAL` · `SEM_OCORRENCIA` ·
`INDISPONIVEL` · `REQUER_INTERVENCAO_MANUAL` · `ERRO`.

Mapeamento para a cobertura: `municipality_coverage.situation`
(`DISPONIVEL`/`INDISPONIVEL`/`DEPENDE_AUTENTICACAO`/…) descreve a fonte; o status acima
descreve uma **execução** específica.

---

## 5. Camadas (serviços futuros, fora da Etapa B)

| Serviço | Responsabilidade | Etapa |
|---|---|---|
| `DebtQueryService` | Orquestra o plano de consulta a partir da oportunidade + cobertura | E |
| Adaptadores concretos | Implementam `MunicipalDebtProvider` por município/tipo | E/F (por viabilidade) |
| `DebtNormalizationService` | Normaliza resultado heterogêneo no modelo comum | E |
| `DebtEvidenceService` | Grava evidência (reusa `Evidence`) | E |
| `DebtReconciliationService` | Detecta divergência/duplicidade (não soma o mesmo lançamento) | E/F |

A Etapa B entrega apenas o que estes serviços **consultarão** como configuração: a
matriz de cobertura e o cadastro de fontes.

---

## 6. Fronteira explícita da Etapa B

**Implementado:** matriz de cobertura (`municipality_coverage`), cadastro/edição de
fontes, vocabulários canônicos (nível/situação/método), APIs e UI administrativas,
inventário de fontes oficiais (documental).

**NÃO implementado (deliberadamente):** nenhum `MunicipalDebtProvider` concreto,
nenhum `DebtQueryService`, nenhuma tabela `debt_query`, nenhum worker, nenhuma chamada
HTTP a portal. Esses itens dependem de autorização e de confirmação de viabilidade por
município, e pertencem às Etapas E/F.

# SEQUENCING — Ordem de execução M0 × B1 (sem conflitos)

> **Status:** PROPOSTO (revisão documental; **nada implementado**). Consolida e ordena
> `PLAN-M0-API-MODULARIZATION.md` + `PLAN-B1-WORKFLOW-ENGINE.md`. Objetivo: entregas **pequenas,
> testáveis e independentes**, evitando que M0 e B1 editem os **mesmos arquivos** ao mesmo tempo.

## 1. O conflito a evitar

Os dois épicos competem por **dois arquivos quentes**:
- **`backend/app/main.py`** — M0 move rotas para routers; B1 adiciona o router de workflow.
- **`backend/app/models.py`** — B1 adiciona modelos e colunas `opportunity_id`.

Regra de ouro de sequenciamento: **nunca dois PRs em revisão simultânea tocando o mesmo arquivo
quente.** Resolvemos isso com uma ordem que separa claramente o que é "arquivo novo" (sem
conflito) do que edita arquivo compartilhado.

## 2. Três trilhas

| Trilha | Toca arquivos quentes? | Pode rodar cedo/paralela? |
|---|---|---|
| **T-A (M0 infra + domínios não-workflow)** | `main.py` | sim, começa primeiro |
| **T-B (B1 núcleo em arquivos NOVOS)** | não (`models.py` só ao final da trilha) | **sim, em paralelo a T-A** |
| **T-C (integração: router workflow + colunas opportunity_id)** | `main.py` + `models.py` | **não** — depende de T-A e T-B |

- **T-B** cria `workflow_rules.py`, `workflow_engine.py` (puro) e testes — **arquivos novos**,
  zero conflito com M0. Pode avançar enquanto o M0 reorganiza routers.
- **T-C** é o ponto de encontro: só entra quando a infra de routers (M0.1) existe e o engine puro
  (T-B) está pronto. Aí se adiciona o router `workflow` e as colunas `opportunity_id`.

## 3. Ordem definitiva (sequência de PRs)

```
# FASE A — habilitar (M0 mínimo) + B1 puro em paralelo
M0.1  routers/ + deps.py + baseline OpenAPI + test_openapi_contract  (move health, hubs)   [T-A]
B1.1  models: Opportunity + OpportunityWorkflow + WorkflowTransition (migrations 0018/0019) [T-B]*
B1.2  workflow_rules.py v1 + workflow_engine.py (puro, sem DB)                              [T-B]

# FASE B — M0 avança por domínios "frios" (não-workflow) ; B1 ganha serviço
M0.2..M0.k  mover domínios que o workflow NÃO altera (market, costs_debts, occupancy,
            evidence, auctioneers, documents, registration, notices, legal_central)        [T-A]
B1.3  workflow_service.py: create_opportunity + apply_transition (append-only) + DomainEvent [T-B]

# FASE C — integração (ponto único de encontro; serializar)
B1.4  colunas opportunity_id NULLABLE (migration 0020)                                     [T-C]
M0.k+1 mover domínios que o workflow consulta (financial, analysis, checklist,
       due_diligence, legal_processes, post_auction) — já com leitura por oportunidade    [T-A/T-C]
B1.5  build_opportunity_context + gates de leitura F0–F8 (reuso dos domínios)              [T-C]
B1.6  hard stops + bloqueio F8 + score por dimensão v1                                     [T-C]
B1.7  invalidate_on_event (reabertura/invalidação)                                         [T-C]
C1    router workflow.py + include_router (entra no main já modularizado)                  [T-C]
B1.8  opportunity_dossier (GET puro)                                                        [T-C]

# FASE D — UI + finalização
M0.final  mover properties; main.py vira bootstrap + include_router                        [T-A]
B1.9  frontend: dashboard + linha do tempo + próxima ação                                  [T-B-fe]
B1.10 (OPCIONAL, aprovação explícita adicional) backfill legado (migration 0021)           [T-C]
```

`*` B1.1 toca `models.py` **adicionando classes ao final** (não edita classes existentes). Para
evitar colisão com um eventual M0 que também mexesse em `models.py` — M0 **não** mexe em
`models.py` (só move rotas). Então B1.1 e M0.x não colidem. A edição de `models.py` que adiciona
**colunas** em classes existentes (B1.4) é isolada na FASE C.

## 4. Regras de serialização (quando algo precisa ser sequencial)

1. **`main.py`**: só um PR por vez o edita. O router `workflow` (C1) entra **depois** de M0.1
   (infra de routers existe) e, idealmente, depois dos domínios que ele consulta já migrados —
   mas no mínimo depois de M0.1. Nunca abrir C1 junto com um M0.x que ainda mexe em `main.py`.
2. **`models.py`**: B1.1 (adição de classes) e B1.4 (adição de colunas) são **PRs distintos e
   sequenciais**; nenhum outro PR edita `models.py` entre eles.
3. **Migrations**: uma por PR, numeração sequencial (`0018`→`0019`→`0020`→`0021`), nunca duas
   abertas em paralelo (evita conflito de `down_revision`/head).
4. **Serviços de leitura** (`latest_execution`, `build_finance`, etc.) ganham parâmetro opcional
   em **B1.5**, depois que as colunas existem (B1.4). Antes disso, assinatura intacta.

## 5. Independência e testabilidade de cada etapa

- **M0.x**: testável isoladamente por **diff de OpenAPI** + testes HTTP do domínio movido.
  Reversível (basta reverter o PR). Não depende de B1.
- **B1.1/B1.2**: testáveis sem tocar fluxo existente (modelos novos + engine puro com unit tests
  determinísticos). B1.2 não precisa de DB.
- **B1.3+**: cada PR tem seu conjunto de testes (transições, isolamento, hard stop, invalidação).
- **Nada** de uma etapa quebra a anterior: tudo aditivo; rotas e dados atuais preservados.

## 6. Pontos de decisão/gate dentro da sequência

- **Gate 0 (agora):** aprovação desta revisão documental.
- **Gate 1:** antes de B1.4 (colunas `opportunity_id`) — confirmar a matriz da
  `MATRIZ-OPPORTUNITY-ID.md` (incl. decisão `post_auctions` A/B).
- **Gate 2:** antes de B1.10 (backfill `0021`) — aprovação **explícita adicional** + `pg_dump`.

## 7. Resumo da ordem definitiva (uma linha)

> **M0.1 (infra) → [B1.1+B1.2 em paralelo] → M0 domínios frios → B1.3 → B1.4 (colunas) → M0
> domínios consultados → B1.5→B1.6→B1.7 → router workflow (C1) → B1.8 → M0.final (properties) →
> B1.9 (UI) → [opcional, com aprovação] B1.10 backfill.**

Sem nenhum momento em que dois PRs editem `main.py` ou `models.py` simultaneamente.

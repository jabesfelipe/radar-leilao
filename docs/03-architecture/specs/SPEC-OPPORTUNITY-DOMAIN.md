# SPEC — Domínio de Oportunidade (Imóvel × Oportunidade × Processo × Dossiê)

> **Status:** PROPOSTO (especificação; nada implementado). Preserva 633/V1–V9/`llm_runs`.
> Decisões de base em `ADR-WORKFLOW-ARCHITECTURE.md`. Modelagem de tabelas em
> `MODEL-DATA-WORKFLOW.md`.

## 1. Conceitos e fronteiras

| Conceito | Pergunta que responde | Estabilidade | Entidade |
|---|---|---|---|
| **Imóvel** (`Property`) | *Que bem é este?* (endereço, matrícula, tipo) | Estável no tempo | existente |
| **Oportunidade** (`Opportunity`) | *Que oferta de aquisição estou avaliando agora?* (este leilão/edital/preço/data) | Efêmera; pode haver várias por imóvel | **nova** |
| **Processo de Análise** | *O que a avaliação técnica concluiu nesta oportunidade?* (versões V1..Vn, veredito) | Versionado dentro da oportunidade | existente, re-ancorado |
| **Workflow** | *Em que fase está e o que falta para avançar?* | Estado vivo da oportunidade | **novo** (ver SPEC-WORKFLOW-ENGINE) |
| **Dossiê** | *Qual a visão consolidada de tudo isto?* | Projeção read-only | sem tabela (agrega) |

### Regra de ouro
Um **Imóvel** é uma coisa; uma **Oportunidade** é uma decisão de investimento sobre esse imóvel
num momento. **1 Imóvel : N Oportunidades.** Históricos de oportunidades diferentes **não se
misturam** — cada uma tem seu próprio ciclo de análise, workflow e veredito.

## 2. Cardinalidades

```
Property (1) ───< (N) Opportunity (1) ───(1) OpportunityWorkflow
                           │
                           ├───< (N) Analysis        [re-ancorada: opportunity_id nullable]
                           ├───< (N) Verdict          [via analysis/versão]
                           ├───< (N) ChecklistExecution
                           ├───< (N) Risk
                           ├───< (N) Auction/AuctionNotice (oferta concreta)
                           ├───< (N) DueDiligenceFront
                           ├───< (0..1) PostAuction
                           └───< (N) DomainEvent / WorkflowTransition

Property (1) ───< (N) Document      [documentos do IMÓVEL, compartilháveis entre oportunidades]
```

Notas:
- **Documentos** pertencem ao **imóvel** (matrícula, plantas) e podem ser **referenciados** por
  várias oportunidades. Documentos específicos de uma oferta (um edital de um leilão) podem ser
  marcados por `opportunity_id` quando fizer sentido — decisão fina no MODEL-DATA. Nunca duplicar
  o arquivo; no máximo referenciar.
- **Pós-Arrematação** é 0..1 por oportunidade (só quando a oportunidade vira aquisição).

## 3. Entidade `Opportunity` (especificação funcional)

Campos propostos (tipos/índices no MODEL-DATA):
- `id`, `property_id` (FK, obrigatória — toda oportunidade é de um imóvel).
- `codigo` / rótulo legível (ex.: "633 — 2º leilão 10/2026").
- `origin` / `portal` / `external_id` (origem da oferta — reusa semântica de `PropertySource`).
- `modality` (**F1**: `JUDICIAL` / `EXTRAJUDICIAL_ALIENACAO_FIDUCIARIA` /
  `EXTRAJUDICIAL_OUTRA_GARANTIA` / `VENDA_DIRETA` / `INDEFINIDO`) + evidência exigida.
- `status` de alto nível da oportunidade (ver §4).
- `is_legacy` (bool) — marca a oportunidade criada por backfill para cobrir o passado.
- `opened_at` / `closed_at` / `close_reason`.
- `created_by` / `updated_by` (quando houver auth; por ora `actor` textual como em `EntityHistory`).

> **Premissas financeiras**: hoje vivem em `Auction.financial_assumptions` (JSON). Conceitualmente
> são "da oportunidade". Na transição, continuam sendo lidas de onde estão; não há reescrita.
> Consolidação futura (mover para a oportunidade) é decisão posterior, fora de B1.

## 4. Ciclo de vida da Oportunidade (status de alto nível)

Distinto das **fases** (F0–F13, que são do workflow). O status resume a situação:

| Status | Significado |
|---|---|
| `EM_PROSPECCAO` | Capturada, ainda em triagem (F0/F1). |
| `EM_ANALISE` | Due diligence / viabilidade em andamento (F2–F7). |
| `EM_DECISAO` | No comitê (F8). |
| `APROVADA` | Comitê aprovou; aguardando/participando do leilão (F9). |
| `ADQUIRIDA` | Arrematada e em pós-arrematação (F10–F12). |
| `ENCERRADA` | Concluída (vendida/locada/mantida) (F13). |
| `DESCARTADA` | Abandonada com justificativa (a qualquer momento). |
| `PERDIDA` | Não arrematada no leilão. |

Transições de status são **derivadas** do avanço de fase do workflow (não editadas à mão, salvo
`DESCARTADA`, que é ação humana explícita com justificativa).

## 5. Dossiê (projeção read-only)

O Dossiê **não é tabela**; é uma **view/serviço de leitura** que agrega, por oportunidade:
- identificação do imóvel + dados da oferta (Auction/AuctionNotice);
- documentos e evidências (Document/DocumentVersion/Evidence);
- estado do workflow (fase, pendências, bloqueios, próxima ação);
- resultados por domínio (checklist, riscos, veredito, financeiro, due diligence, jurídico);
- histórico de decisões e transições (WorkflowTransition/EntityHistory).

Regra: **GET do dossiê nunca dispara LLM, análise ou custo externo** (consulta pura).

## 6. Impacto no que existe (resolução legado × oportunidade)

- Consultas de histórico passam a aceitar um `opportunity_id` **opcional**. Quando ausente ⇒
  comportam-se como hoje (todo o histórico do imóvel = oportunidade legada).
- Serviços como `latest_execution(prop)`, `juridical_overview(db, prop)`,
  `due_diligence_overview(db, prop)`, `build_finance(prop)` continuam funcionando por imóvel;
  a evolução para filtrar por oportunidade é **aditiva** (parâmetro opcional), preservando a
  assinatura atual durante a transição.
- **Imóvel 633**: sem backfill, continua com uma única oportunidade implícita (legada) contendo
  V1–V9 — idêntico ao atual.

## 7. Invariantes do domínio

1. Toda `Opportunity` pertence a exatamente um `Property`.
2. Um `Property` pode ter 0..N `Opportunity`; no máximo as "vivas" que o usuário abrir (não há
   limite técnico, mas a UI destaca a corrente).
3. Histórico de análise (Analysis/Verdict/Checklist/Risk) de uma oportunidade **nunca** é
   reatribuído a outra.
4. A oportunidade **legada** (`is_legacy=true` ou `opportunity_id IS NULL`) é imutável quanto à
   sua associação com o passado.
5. Documento é do imóvel; referência por oportunidade não duplica o arquivo nem a versão.

## 8. Fora de escopo desta spec
- Implementação de tabelas/migrations (ver MODEL-DATA — e só após aprovação).
- Consolidação de `financial_assumptions` para a oportunidade.
- Multi-tenant / usuários (épico M, auth/RBAC).

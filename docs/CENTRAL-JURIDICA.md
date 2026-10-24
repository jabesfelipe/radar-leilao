# Central Jurídica (camada transversal de conhecimento jurídico)

Evolução reuse-first do Radar Leilão. A Central Jurídica **não é "uma página que
lista leis"**: é uma base de conhecimento jurídico curada que aparece **em contexto
de decisão** — ao lado dos itens do checklist, nas etapas de desocupação/posse, no
tributário e na síntese jurídica do imóvel. Nenhum módulo foi duplicado e a
arquitetura não foi reescrita.

## Princípios de integridade

- **Nunca fabricar norma.** O **texto oficial** (`official_text`, verbatim do
  dispositivo vigente) é guardado **separado** da **orientação prática**
  (`practical_note`, paráfrase do Método Radar). A UI sempre os distingue.
- **Vigência e verificação explícitas.** Cada fonte/dispositivo carrega
  `verification_status` (`VERIFICADO` / `PENDENTE` / `DESATUALIZADO`) e `in_force`.
  O que não foi conferido na fonte oficial aparece como pendência, nunca como fato.
- **Os 27 `canonical_key` do Checklist Mestre são preservados.** A Central apenas os
  **enriquece** com base legal (via vínculo por `canonical_key`), sem alterar
  `CHECKLIST_MASTER` nem o `origin` dos itens.
- **Sem LLM nos caminhos de leitura.** A biblioteca, as referências e a síntese são
  determinísticas. A busca usa similaridade vetorial quando há `OPENAI_API_KEY`;
  sem chave, cai para **busca textual** (nenhuma análise de IA é disparada).

## Reutilização (o que NÃO foi duplicado)

| Necessidade | Reusa | Novo |
|---|---|---|
| Busca semântica | `KnowledgeItem` (kind `LEGAL_LIBRARY`) + embeddings (`rag/embeddings`) | — |
| Evidências | `Evidence`/`EvidenceLink` | — |
| Rastreabilidade | `DomainEvent`/`EntityHistory` (`/historico`) | — |
| Situação jurídica do imóvel | `juridical_overview` (determinístico) | enriquecimento com base legal |
| Checklist | 27 `canonical_key` existentes (`checklist.py`) | vínculo regra↔item (sem alterar o checklist) |
| Correlação processo×imóvel | `legal_correlation` (concern distinto) | — |

## Entidades novas (migration `0017_central_juridica`)

Tudo aditivo e reversível (nenhum dado existente é tocado):

- `legal_sources`: a norma (lei/código/súmula/jurisprudência) — identificação,
  apelido, link oficial, ano, vigência, `verification_status`, resumo neutro.
- `legal_provisions`: o dispositivo concreto (artigo/§/inciso) — `official_text`
  (verbatim) **separado** de `practical_note` (paráfrase), `contexts`, `tags` e
  `knowledge_item_id` (liga ao `KnowledgeItem` indexado por RAG).
- `legal_rules`: a regra prática do Método Radar, ancorada em um `provision_id`.
- `legal_rule_checklist_links`: vínculo regra ↔ item do checklist por
  `canonical_key` (string estável, não FK) — o mecanismo que enriquece os 27 itens
  sem tocar na definição canônica.

Vocabulário: `LEGAL_SOURCE_TYPES`, `LEGAL_VERIFICATION_STATUS`, `LEGAL_RULE_KINDS`
(`REQUISITO`/`RISCO`/`ORIENTACAO`/`PRAZO`/`RESPONSABILIDADE`), `LEGAL_CONTEXTS`
(`LEILAO`/`ARREMATACAO`/`MATRICULA`/`CONSOLIDACAO`/`DESOCUPACAO`/`POSSE`/
`TRIBUTARIO`/`LOCACAO`/`GERAL`).

## Conteúdo curado (seed idempotente)

O catálogo vive em `backend/app/legal_catalog.py` (dado estático, revisável). O seed
(`legal_service.seed_legal_catalog`) materializa por `slug` sem duplicar nem
sobrescrever edições humanas. Fontes reais já cadastradas (texto oficial + link):

- **Lei 9.514/97** — art. 26 (consolidação), art. 27 (dois leilões), art. 37-A
  (taxa de ocupação).
- **Código Civil** — art. 1.228 (reaver a coisa/posse), art. 447 (evicção subsiste
  em hasta pública).
- **CPC/2015** — art. 903 (perfeição da arrematação judicial).
- **Lei do Inquilinato (8.245/91)** — art. 8º (locação averbada × denúncia em 90d).
- **CTN** — art. 130 (sub-rogação de tributos no preço da arrematação), art. 131, I.

Regras práticas vinculadas ao checklist: intimação da mora, dois leilões, taxa de
ocupação, imissão na posse, evicção, locação averbada, tributos/sub-rogação e
perfeição da arrematação judicial.

## Endpoints

- `GET /api/juridico/biblioteca` — visão agregada: fontes, dispositivos, regras e
  cobertura dos itens do checklist. Semeia o catálogo (idempotente) na 1ª leitura.
- `GET /api/juridico/biblioteca/busca?q=&contexto=&limite=` — busca (vetorial quando
  há embeddings/chave; caso contrário, textual determinística).
- `GET /api/juridico/referencias/checklist/{canonical_key}` — regras + base legal
  aplicáveis a um item do checklist ("Base legal e orientações").
- `GET /api/juridico/referencias/contexto/{contexto}` — regras por etapa/contexto
  (ex.: `DESOCUPACAO`, `LEILAO`).
- `GET /api/imoveis/{id}/juridico/central` — síntese jurídica do imóvel (reuso de
  `juridical_overview`) + referências legais por item com base associada.

## Frontend

Aba **Central Jurídica** no dossiê do imóvel (`CentralJuridicaSection`):

1. **Situação jurídica do imóvel** (reaproveita a síntese determinística).
2. **Base legal por item do checklist** (conhecimento em contexto).
3. **Biblioteca jurídica**: busca (textual/semântica) + fontes curadas, com o
   **texto oficial** (citação) visualmente separado da **orientação prática**.

Serviço: `frontend/src/services/legal.ts` (reusa `request`/`PropertiesServiceError`).

## Sobre o histórico "136 + 27 → 45 regras"

A base canônica **implementada** do produto é o Checklist Mestre com **27
`canonical_key`** (`backend/app/checklist.py`). O conjunto histórico de 136/163
itens brutos e 45 regras canônicas descrito na documentação de origem é **material
de curadoria** e segue registrado como pendência em
`docs/TODO-CENTRAL-JURIDICA.md` — não foi reinventado para evitar fabricação de
conteúdo inexistente no código.

## Testes (evidência real)

- Backend: migration `0017_central_juridica` aplicada (head). `tests/test_central_juridica.py`
  (11 testes) verde junto a `test_juridico_integracao_e2e.py` e `test_checklist.py`.
  Busca em modo **textual** sem `OPENAI_API_KEY` (nenhum LLM disparado).
- Frontend: `tsc --noEmit` OK; `vitest run` **137 passed (22 arquivos)** (+5 em
  `CentralJuridicaSection.test.tsx`).
- Imóvel 633 intacto (9 análises V1–V9, zero V10) — a Central não cria análise nem
  versão.

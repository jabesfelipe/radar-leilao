# TASK 51 — Primeiro E2E REAL com imóvel da Caixa (relatório diagnóstico)

> Task **diagnóstica**. Objetivo: executar o fluxo real com **imóvel e documentos
> reais da Caixa** e registrar exatamente **onde funciona e onde quebra**.
> **Não corrigir** nada nesta task (as correções ficam para a TASK 52).
>
> Data da execução: 20/09/2026 · Ambiente: Windows / PowerShell · Python 3.13.9
> Backend: FastAPI + PostgreSQL/pgvector · LLM: provider OpenAI · Normalizador: MarkItDown

As observações estão classificadas em categorias que **não se misturam**:
**CONFIRMADO POR EXECUÇÃO REAL**, **CONFIRMADO POR CÓDIGO/TESTE**, **NÃO TESTADO**,
**BLOQUEADO**, **GAP REAL**, **HIPÓTESE**.

---

## Resumo executivo (não mascarado)

Com os dados/documentos reais fornecidos, o E2E avançou além da TASK 51 anterior:
os **PDFs reais foram baixados e passaram pelo pipeline documental real** (normalizer).
O fluxo **quebrou de forma real na etapa de normalização** por falta de dependência
de PDF, e os passos seguintes (persistência, extração, RAG, Agents, LangGraph,
Checklist, Risk, Verdict, Dossiê, Histórico, reanálise) **não puderam ser executados**
porque dependem de PostgreSQL (indisponível) e/ou do markdown normalizado (não gerado)
e/ou de LLM (sem chave). Nada foi simulado.

Situação por bloqueio:

- **DB (PostgreSQL/pgvector): BLOQUEADO.** `DB_CONNECT=fail: OperationalError`; nada
  escutando em `127.0.0.1:5432`; sem Docker/docker-compose e sem Postgres nativo
  (`pg_ctl`/`psql`/`initdb` ausentes). Subir o banco exigiria instalar infraestrutura,
  o que a task proíbe.
- **LLM: BLOQUEADO — `LLM_BLOCKED = true`.** Sem `.env`; `OPENAI_API_KEY` e
  `LLM_API_KEY` não definidos. Não foi criado provider nem mock (proibido).
- **Pipeline documental: GAP REAL** confirmado por execução (ver §7).

---

## 1. Imóvel utilizado

**COND PARQUE ARVOREDO RESIDENCIAL CLUBE** — dados reais fornecidos pela task
(usados exatamente como recebidos; nada inventado):

| Campo | Valor |
|---|---|
| Tipo | Apartamento · 3 quartos · 2 vagas |
| Nº do imóvel (Caixa) | 155552876506-4 |
| Matrícula | 25278 · Comarca CURITIBA-PR · Ofício 07 |
| Inscrição imobiliária | 57000970088001 |
| Área total / privativa | 102,71 m² / 109,08 m² |
| Endereço | RUA FRANCISCO DEROSSO, 375, APTO 53, TORRE 05B, PAV. 5, XAXIM, CEP 81710-000, CURITIBA-PR |
| Leilão | SFI · Edital 0044/0226 - CPA/RE · Item 258 · Leiloeiro WERNO KLÖCKNER JÚNIOR |
| Avaliação | R$ 370.000,00 |
| Mínimo 1º leilão / 2º leilão | R$ 370.000,00 / R$ 222.000,00 |
| Datas | 1º: 28/09/2026 10h00 · 2º: 02/10/2026 10h00 |
| Averbação de leilões negativos | Não se aplica |
| Despesas | Condomínio e tributos por conta do comprador |
| Pagamento | Recursos próprios; permite FGTS conforme condições da Caixa |

## 2. Documentos utilizados — **CONFIRMADO POR EXECUÇÃO REAL**

Ambos baixados dos endpoints oficiais da Caixa (não sintéticos):

| Documento | URL | Tamanho | Tipo | Páginas (aprox.) | SHA-256 |
|---|---|---|---|---|---|
| Matrícula | `venda-imoveis.caixa.gov.br/editais/matricula/PR/1555528765064.pdf` | 538.507 bytes | PDF válido (`%PDF`) | ~3 | `e0b83814500229aa2ccbd32eb68d9836c76fdfe11acd64e9f3be3ab8db58a273` |
| Edital | `venda-imoveis.caixa.gov.br/editais/EL00440226CPARE.PDF` | 1.126.227 bytes | PDF válido (`%PDF`) | ~142 | `4e5926d9c35c4356e9f7569212564d5eeafd2b168937e3b7c466c396e835d93b` |

> A contagem ~142 páginas do edital confere com a informação da task. Os arquivos
> permaneceram **apenas no ambiente local** (`_e2e_local/`), **não versionados**.

## 3. Fluxo executado (real)

Download dos PDFs → Pipeline documental real (`DocumentNormalizer` → `chunk_markdown`).
A partir daí, **bloqueio na normalização** (§7). Etapas posteriores não executadas
por dependência de DB/markdown/LLM.

## 4. Etapas que funcionaram — **CONFIRMADO POR EXECUÇÃO REAL**

- **Download dos documentos reais** (matrícula e edital), com verificação de que são
  PDFs válidos, tamanho e hash.
- **Invocação real do `DocumentNormalizer`** do projeto sobre os PDFs reais (sem
  pipeline paralelo, sem alterar o normalizer) — a chamada aconteceu e retornou erro
  real e observável (ver §7). Ou seja: o ponto de quebra foi **exercitado de verdade**.

## 5. Etapas BLOQUEADAS / NÃO TESTADAS

| Etapa | Status | Motivo |
|---|---|---|
| Cadastro do imóvel/leilão/matrícula/edital (persistência) | **BLOQUEADO** | PostgreSQL indisponível |
| Normalização PDF→markdown | **GAP REAL** | dependência de PDF ausente (§7) |
| Chunks / embeddings | **NÃO TESTADO** | sem markdown normalizado; embeddings exigem LLM |
| RAG (textual/vetorial/híbrido) | **NÃO TESTADO** | sem chunks persistidos; sem DB |
| Extração (matrícula/edital) | **NÃO TESTADO** | exige DB + RAG + LLM |
| Agents (Document/Jurídico/Financeiro/Mercado/Checklist) | **BLOQUEADO** | exigem LLM (`LLM_BLOCKED`) + DB |
| LangGraph (LOAD→RETRIEVE→RUN→CONSOLIDATE→Risk→Verdict) | **NÃO TESTADO (real)** | depende de DB e agents; topologia já validada por teste (§11) |
| Checklist Mestre (alimentado por findings) | **NÃO TESTADO** | sem findings de agents |
| Risk Engine / Verdict Engine | **NÃO TESTADO (neste E2E)** | exigem DB; já validados por teste (§13) |
| Dossiê final / Hub | **BLOQUEADO** | sem DB |
| Histórico | **BLOQUEADO** | sem DB |
| Reanálise incremental (v1→v2) | **NÃO TESTADO** | exige DB + análise base |

## 6. Cadastro do imóvel — GAPs DE CONTRATO (HIPÓTESE, por leitura de contrato)

Não foi possível cadastrar de fato (DB bloqueado). Comparando os dados reais com os
contratos atuais (`schemas.py`), os seguintes dados reais **não têm campo
correspondente** e ficam registrados como **GAP DE CONTRATO** (a confirmar na TASK 52;
**não** alterados aqui):

- **Número do imóvel Caixa** (`155552876506-4`): sem campo no modelo `Property`.
- **Inscrição imobiliária** (`57000970088001`): sem campo.
- **Duas datas de leilão simultâneas** (1º 28/09 e 2º 02/10): `AuctionCreate`/
  `AuctionNotice` guardam um `auction_date`/`auction_stage` por registro, não o par.
- **Nº do item do edital** (`258`) e **identificador do edital** (`0044/0226 - CPA/RE`):
  `AuctionNoticeCreate` tem `identifier` (texto livre) mas não `item`/lote dedicado.
- **Área total vs. área privativa**: `Property.area_m2` é único; os dois valores reais
  (102,71 e 109,08) não cabem separadamente.
- **Responsabilidade por condomínio/tributos** e **FGTS/forma de pagamento**: sem
  campos estruturados (poderiam ir para `observations` em texto livre).

> Estes GAPs são **hipóteses de leitura de contrato**, não confirmados por execução de
> cadastro (bloqueada pelo DB). Não representam extração real do edital.

## 7. Problemas de extração / pipeline documental — **GAP REAL (execução)**

**PROBLEMA:** `DocumentNormalizer.normalize()` **falha nos dois PDFs reais**.

- **EVIDÊNCIA (saída real):** `RuntimeError: Não foi possível normalizar o documento
  com MarkItDown: ... PdfConverter threw MissingDependencyException ... the
  dependencies needed to read .pdf files have not been installed.` — para
  `matricula.pdf` e `edital.pdf`.
- **CAUSA PROVÁVEL (confirmada por sonda):** `markitdown` está instalado, mas o backend
  de PDF **`pdfminer` está ausente** (`pdfminer = False`). O MarkItDown precisa do
  extra de PDF (ex.: `markitdown[pdf]` / `pdfminer.six`) para ler PDFs.
- **AGRAVANTE (leitura de código):** o *fallback* do `DocumentNormalizer` só trata
  `.txt/.md/.csv`; para `.pdf` ele **re-levanta `RuntimeError`**. Ou seja, sem a
  dependência de PDF o pipeline **não tem caminho alternativo** para documentos reais
  (que são sempre PDF na Caixa).
- **IMPACTO:** sem normalização não há markdown → não há chunks → não há embeddings →
  não há RAG → extração/Agents/Checklist/Risk/Verdict ficam sem insumo documental.
  É o **primeiro ponto de quebra do E2E real**.
- **PRÓXIMA AÇÃO SUGERIDA (TASK 52):** instalar/depender explicitamente do backend de
  PDF do MarkItDown (ex.: `markitdown[pdf]`/`pdfminer.six`) no `requirements` do
  backend; reexecutar o pipeline sobre estes mesmos PDFs; observar OCR/tabelas do
  edital (~142 páginas) e a extração estruturada de matrícula.

## 8. Problemas de rastreabilidade — **NÃO TESTADO**

Rastreabilidade (finding→evidence→document→version→page/chunk) não pôde ser
observada: depende de chunks/RAG/Agents, todos bloqueados a montante. Não há dado real
para afirmar sucesso ou falha aqui.

## 9. Problemas de RAG — **NÃO TESTADO**

Nenhuma consulta RAG executada (sem chunks persistidos, sem DB, embeddings exigiriam
LLM). As perguntas propostas na task (valor do 2º leilão, matrícula, responsáveis por
condomínio/tributos, data do 2º leilão, item, endereço) **não foram respondidas** por
não haver índice.

## 10. Problemas dos Agents — **BLOQUEADO (LLM)**

Nenhum Agent executado: todos dependem de LLM (`LLM_BLOCKED = true`) e de DB. Não há
findings/evidências reais para reportar. **Não** foram criados findings falsos.

## 11. Problemas do LangGraph — **CONFIRMADO POR CÓDIGO/TESTE (não neste E2E)**

Topologia `LOAD_CONTEXT → RETRIEVE_RAG → RUN_AGENTS → CONSOLIDATE` validada por testes
unitários existentes (TASK 26/27). **Não foi exercitada neste E2E real** (depende de DB
e Agents). Nenhum problema novo observado — apenas não testado com dado real.

## 12. Problemas do Checklist — **NÃO TESTADO**

O Checklist Mestre é semeado no cadastro e alimentado por findings dos Agents. Sem
cadastro (DB) e sem Agents (LLM), não foi possível verificar se as evidências chegam
aos itens. Objetivo central da task que permanece **não verificado com dado real**.

## 13. Problemas de Risk/Verdict — **CONFIRMADO POR CÓDIGO/TESTE (não neste E2E)**

`RiskEngine`/`VerdictEngine` são determinísticos e já validados por testes unitários
(TASK 31/32) e pelos testes de integração da TASK 50 (contra DB). **Não exercitados
neste E2E** (DB bloqueado).

## 14. Bloqueios por LLM / API / configuração

- **LLM_BLOCKED = true.** Sem `.env`, sem `OPENAI_API_KEY`/`LLM_API_KEY`. Provider
  OpenAI é o único suportado. Não simulado.
- **DB BLOQUEADO.** PostgreSQL/pgvector indisponível; sem Docker e sem Postgres nativo.
- **Dependência de PDF ausente** para o MarkItDown (§7).

## 15. Lista objetiva de correções necessárias para a TASK 52

Ordenada por dependência:

1. **Instalar o backend de PDF do MarkItDown** (`markitdown[pdf]` / `pdfminer.six`) e
   fixá-lo no `requirements` do backend. Reexecutar a normalização sobre a
   matrícula/edital reais já baixados.
2. **Rever o *fallback* do `DocumentNormalizer`** para PDFs (hoje só há fallback para
   texto), decidindo comportamento quando o backend de PDF falha (ex.: erro claro vs.
   OCR). — decisão de design da TASK 52.
3. **Prover runtime de execução do E2E:** subir PostgreSQL/pgvector (docker-compose já
   existe) + migrations, e fornecer `OPENAI_API_KEY` — sem o que Agents/RAG/extração
   não rodam.
4. **Rever contratos** para os GAPs do §6 (nº do imóvel Caixa, inscrição imobiliária,
   duas datas de leilão, item/lote do edital, área total × privativa, responsabilidades
   e FGTS) — **somente após** confirmar contra o edital/matrícula reais já normalizados.
5. **Reexecutar o E2E completo** (cadastro → extração → RAG → Agents → LangGraph →
   Checklist → Risk → Verdict → Dossiê → Histórico → reanálise) e converter os itens
   "NÃO TESTADO" acima em confirmações reais.

> Nenhuma dessas correções foi implementada nesta task (diagnóstica). Nenhum contrato,
> modelo, Agent, LangGraph, RAG, Risk, Verdict ou infraestrutura foi alterado.

---

## Notas de método

- Documentos reais baixados e passados pelo pipeline real; **nada sintético**.
- **Nenhuma** falha foi mascarada como sucesso; **nenhum** finding/resposta/evidência
  foi inventado; **nenhum** mock de LLM foi usado.
- Itens sobre etapas não executadas estão marcados como **NÃO TESTADO/BLOQUEADO**, e
  os GAPs de contrato como **HIPÓTESE** até confirmação com documento real normalizado.
- Arquivos locais de teste (PDFs e scripts de sonda) **não** foram adicionados ao Git.


---

# TASK 51B — Segunda execução (preparar runtime + repetir E2E)

> Data: 20/09/2026 · Mesmo imóvel (COND PARQUE ARVOREDO — nº Caixa 155552876506-4,
> matrícula 25278, edital 0044/0226 - CPA/RE, item 258, Curitiba/PR) e mesmos
> documentos oficiais. Objetivo: remover o bloqueio de PDF, disponibilizar o
> Postgres/pgvector existente, configurar LLM se houver chave, repetir o E2E e
> encontrar o próximo breakpoint real. **Sem corrigir GAPs de negócio.**

## Ambiente

- Python 3.13.9 / Windows / PowerShell.
- Sem Docker, docker-compose, `psql` ou `pg_ctl` no ambiente (confirmado).
- Sem `.env`, sem `OPENAI_API_KEY`/`LLM_API_KEY`.

## Dependências instaladas (única alteração de código/ambiente)

- **`backend/requirements.txt`:** `markitdown==0.1.7` → **`markitdown[pdf]==0.1.7`**.
- `pip install "markitdown[pdf]==0.1.7"` instalou: **pdfminer-six 20260107, pdfplumber
  0.11.10, pypdfium2 5.13.0, Pillow 12.3.0, cryptography, cffi, pycparser**.
- Nenhum outro código alterado. Nenhum parser/pipeline/OCR novo. `DocumentNormalizer`
  não foi refatorado.

## Resultado por etapa

| Etapa | Status | Observação (execução real) |
|---|---|---|
| PDF backend do MarkItDown | **OK / GAP REAL resolvido** | Normalização de PDF deixou de lançar `MissingDependencyException`. |
| Normalização matrícula | **OK (com GAP REAL de conteúdo)** | `engine=MarkItDown`, mas só **423 chars** de markdown / **1 chunk**. |
| Normalização edital | **BLOQUEADO (download)** | Re-download retornou **18.341 bytes** = página **anti-bot (Radware CAPTCHA)**, não o PDF. `is_pdf=False`. |
| Chunks | **OK (parcial)** | matrícula: 1 chunk; "edital" (CAPTCHA): 2 chunks — conteúdo inválido. |
| Embeddings | **BLOQUEADO** | Exigem LLM (`LLM_BLOCKED`). Não executado. |
| PostgreSQL | **BLOQUEADO** | `DB_CONNECT=fail: OperationalError`; sem Docker/Postgres nativo. |
| pgvector | **NÃO TESTADO** | Depende do Postgres. |
| RAG | **NÃO TESTADO** | Sem DB e sem embeddings. |
| Extração (matrícula/edital) | **NÃO TESTADO** | Exige DB + RAG + LLM. |
| Agents | **BLOQUEADO** | `LLM_BLOCKED=true`. |
| LangGraph | **NÃO TESTADO (real)** | Topologia já validada por teste; não exercitada aqui. |
| Checklist | **NÃO TESTADO** | Sem findings de Agents. |
| Risk Engine | **NÃO TESTADO (neste E2E)** | Já validado por teste; exige DB. |
| Verdict Engine | **NÃO TESTADO (neste E2E)** | Idem. |
| Dossiê | **BLOQUEADO** | Sem DB. |
| Histórico | **BLOQUEADO** | Sem DB. |

## Detalhe dos achados — CONFIRMADO POR EXECUÇÃO REAL

### PDF: GAP REAL da TASK 51 resolvido
Após `markitdown[pdf]`, a normalização de PDF funciona (engine=MarkItDown, sem exceção
de dependência). Confirmado sobre a matrícula real.

### GAP REAL (novo) — Matrícula é PDF de imagem/escaneado, sem OCR
- **PROBLEMA:** a matrícula normaliza para apenas ~423 chars, contendo somente o
  carimbo de autenticidade do CRI (`"Para consultar a autenticidade ... CNS ... código
  de verificação ..."`). **Nenhum** termo do imóvel foi encontrado no markdown
  (matrícula 25278, titular, averbações, ônus, etc.: todos ausentes).
- **EVIDÊNCIA:** `pdfplumber` sobre o PDF real (538.507 bytes): **2 páginas, ~398 chars
  de texto no total, 2 imagens**. Ou seja, o corpo da matrícula está em **imagem**; a
  única camada de texto é o rodapé de autenticidade.
- **CAUSA PROVÁVEL:** MarkItDown extrai a camada de texto do PDF, mas **não faz OCR**.
  Matrícula real da Caixa vem escaneada → o conteúdo jurídico não é capturado.
- **IMPACTO:** sem o texto da matrícula, a extração estruturada e as evidências
  jurídicas (titular, averbações, consolidação, ônus) ficam sem insumo. É o **próximo
  breakpoint real** do lado documental.
- **PRÓXIMA AÇÃO SUGERIDA (TASK 52+):** decidir estratégia de OCR para PDFs de imagem
  (fora do escopo desta task; não implementar agora).

### BLOQUEADO — Edital não pôde ser re-baixado (anti-bot)
- **PROBLEMA:** o re-download do edital retornou **18.341 bytes** de uma página
  **Radware Bot Manager CAPTCHA** ("Precisamos fazer uma verificação de segurança"),
  não o PDF. `is_pdf=False`.
- **EVIDÊNCIA:** markdown normalizado começa com `"Radware Bot Manager CAPTCHA ...
  Caixa Econômica Federal ... verificação de segurança"`.
- **CAUSA PROVÁVEL:** o site `venda-imoveis.caixa.gov.br` aplica proteção anti-bot que,
  neste momento, bloqueou o download automatizado. (Na TASK 51 o mesmo URL retornou o
  PDF real de 1.126.227 bytes / ~142 páginas — o bloqueio é intermitente.)
- **IMPACTO:** nesta execução, a normalização do edital **não** representa o edital real
  (é a página de CAPTCHA). O edital, portanto, ficou **BLOQUEADO** nesta rodada.
- **PRÓXIMA AÇÃO SUGERIDA:** obter o edital por um canal que não seja bloqueado
  (download manual/local) e reprocessar; não criar integração com a Caixa.

## Bloqueios de ambiente (inalterados desde a TASK 51)

- **PostgreSQL/pgvector: BLOQUEADO** — sem container runtime e sem Postgres nativo;
  não é possível subir sem instalar infraestrutura (proibido pela task).
- **LLM_BLOCKED = true** — sem chave de API; provider OpenAI não pode ser exercitado.

## Até qual etapa o E2E chegou

Avançou **um passo além** da TASK 51: agora o **pipeline documental normaliza PDF**.
A execução real parou logo depois, na **qualidade do conteúdo documental** (matrícula
sem OCR) e em **bloqueios de ambiente** (download do edital, Postgres, LLM). Persistência,
RAG, extração, Agents, LangGraph, Checklist, Risk, Verdict, Dossiê e Histórico
**não foram executados**.

## Próximo breakpoint real

1. **Matrícula escaneada sem OCR** (conteúdo jurídico não extraído) — breakpoint
   documental confirmado.
2. **Ambiente:** Postgres/pgvector e LLM indisponíveis; download do edital bloqueado
   por anti-bot.

## GAPs de negócio confirmados nesta task

**Nenhum.** Os GAPs de contrato levantados na TASK 51 (nº do imóvel Caixa, inscrição
imobiliária, duas datas de leilão, item do edital, área total × privativa,
responsabilidades, FGTS, campos de matrícula) **permanecem como HIPÓTESE** — não foi
possível confirmá-los porque a extração real depende de OCR/DB/LLM ainda indisponíveis.
Nenhum contrato/modelo/regra foi alterado.


---

## TASK 51B — Atualização: runtime via WSL + Docker (correção do ambiente)

> **Correção importante:** as verificações anteriores desta TASK 51B foram feitas a
> partir do **PowerShell/Windows**, onde `docker`/`postgres` não estão no PATH — o que
> levou à conclusão equivocada "PostgreSQL BLOQUEADO". O ambiente oficial é
> **Windows → WSL (Ubuntu) → Docker**. Refeito **dentro do WSL**, o runtime está
> disponível. Esta seção substitui as conclusões de ambiente acima.

### Ambiente real (CONFIRMADO POR EXECUÇÃO REAL, dentro do WSL)

| Item | Status | Evidência |
|---|---|---|
| WSL | **OK** | `wsl -l -v` → Ubuntu, WSL2, Running |
| Docker | **OK** | `docker --version` → 29.8.0 (dentro do WSL) |
| Docker Compose | **OK** | `docker compose version` → v5.5.1 |
| PostgreSQL (container) | **OK** | `docker compose up -d postgres` → `radar-leilao-postgres` **healthy**, `pg_isready` aceitando conexões, `0.0.0.0:5432->5432` |
| Versão do Postgres | **OK** | `16.15 (Debian)` |
| pgvector | **OK** | extensões instaladas: `plpgsql`, **`vector`**, `pg_trgm` (via `infra/postgres/init.sql`) |
| Deps do backend (venv WSL) | **OK** | `pip install -r backend/requirements.txt` → `pip_exit=0`; `markitdown=True`, **`pdfminer=True`**, `fastapi/sqlalchemy/psycopg/pgvector/alembic/langchain/langgraph/openai/httpx = True` |
| Dependência de PDF | **OK / GAP da TASK 51 resolvido** | `pdfminer` presente no runtime; normalização de PDF funciona |
| Migrations (alembic upgrade head) | **ERRO — GAP REAL (novo breakpoint)** | ver abaixo |
| LLM | **BLOQUEADO — `LLM_BLOCKED = true`** | sem `.env` (raiz e `backend/`), `OPENAI_API_KEY`/`LLM_API_KEY` não definidos no WSL |

O repositório é acessado no WSL via `/mnt/c/desenv/poc/radar-leilao` (mesmo repo do
Windows; não houve duplicação de clone). O serviço de banco é `postgres`
(`pgvector/pgvector:pg16`, container `radar-leilao-postgres`), conforme o
`docker-compose.yml` existente — nada foi alterado no compose.

### GAP REAL (novo, CONFIRMADO POR EXECUÇÃO REAL) — cadeia de migrations quebrada

- **PROBLEMA:** `alembic upgrade head` **falha** e o banco fica **sem tabelas**
  (`tables_after_migration = 0`).
- **EVIDÊNCIA (saída real):**
  `sqlalchemy.exc.ProgrammingError: (psycopg.errors.DuplicateColumn) column
  "total_tokens" of relation "llm_runs" already exists`
  `[SQL: ALTER TABLE llm_runs ADD COLUMN total_tokens INTEGER]` · `alembic_exit=1`.
- **CAUSA PROVÁVEL (confirmada por leitura):** a migration inicial
  `0001_fundacao_radar` executa `Base.metadata.create_all(bind)`, criando **todas** as
  tabelas a partir dos **modelos atuais** (que já incluem `llm_runs.total_tokens`). Em
  seguida, `0002_llm_usage_pricing` faz `op.add_column("llm_runs", "total_tokens", ...)`
  — coluna que `0001` já criou → **DuplicateColumn**. Ou seja, `0001` reflete o schema
  **mais recente** (via `create_all`) em vez do schema histórico, colidindo com as
  migrations incrementais `0002+`.
- **IMPACTO:** sem schema aplicado, **nada** que depende do banco roda: cadastro,
  persistência, RAG, extração, Agents, LangGraph, Checklist, Risk, Verdict, Dossiê,
  Histórico, e os testes de integração da TASK 50.
- **PRÓXIMA AÇÃO SUGERIDA (TASK 52):** corrigir a cadeia de migrations (ex.: `0001` não
  usar `create_all` do metadata atual, ou tornar `0002` idempotente/coerente com o
  schema histórico). **Não corrigido aqui** (fora do escopo desta task).

### Estado das etapas do E2E após o runtime WSL

| Etapa | Status | Observação |
|---|---|---|
| WSL / Docker / Postgres / pgvector | **OK** | ver tabela de ambiente |
| Normalização de PDF (matrícula) | **OK** | `pdfminer` presente; matrícula ainda sem OCR (ver GAP de conteúdo acima) |
| Migrations | **ERRO (GAP REAL)** | DuplicateColumn `total_tokens` → 0 tabelas |
| FastAPI (subir/integração TASK 50) | **BLOQUEADO** | depende do schema; migrations falham |
| Embeddings / RAG / Extração | **BLOQUEADO** | dependem de DB + LLM |
| Agents / LangGraph / Checklist / Risk / Verdict | **BLOQUEADO** | dependem de DB e/ou LLM (`LLM_BLOCKED`) |
| Dossiê / Histórico | **BLOQUEADO** | dependem de DB |
| Edital (download) | **BLOQUEADO (intermitente)** | anti-bot Radware no re-download (ver acima) |

### Próximo breakpoint real (atualizado)

1. **Migrations quebradas** (`DuplicateColumn total_tokens` em `0002`, causado pelo
   `create_all` em `0001`) — **este é o próximo breakpoint a corrigir na TASK 52**,
   pois bloqueia todo o restante do E2E que depende do banco.
2. **Matrícula escaneada sem OCR** — breakpoint documental (conteúdo jurídico não
   extraído).
3. **LLM ausente** (`LLM_BLOCKED = true`) e **download do edital** bloqueado por
   anti-bot — bloqueios de ambiente/dados.

### GAPs de negócio confirmados

**Nenhum novo.** Os GAPs de contrato seguem como **HIPÓTESE** — a confirmação depende
de extração real, que está bloqueada pelas migrations/OCR/LLM. Nenhum contrato, modelo,
migration, Agent, LangGraph, RAG, Risk ou Verdict foi alterado nesta task.

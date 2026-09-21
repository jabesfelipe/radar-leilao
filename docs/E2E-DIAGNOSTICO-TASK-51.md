# TASK 51 — Primeiro E2E com imóvel real da Caixa (relatório diagnóstico)

> Task **diagnóstica**. Objetivo: descobrir onde o fluxo real quebra, o que não é
> processado, quais contratos estão incompletos e o que precisa ser corrigido nas
> próximas tasks. Não corrigir tudo, não refatorar, não criar integração/infra.
>
> Data da execução: 20/09/2026
> Ambiente: Windows / PowerShell. Backend FastAPI + PostgreSQL/pgvector. LLM via OpenAI.

---

## Resumo executivo (não mascarado)

O E2E **não pôde ser executado de ponta a ponta** porque as entradas reais exigidas
pela própria task **não existem no repositório** e o runtime necessário **não está
disponível** neste ambiente. Nada foi inventado para simular sucesso.

Bloqueios reais, verificados (não presumidos):

1. **Não há imóvel real da Caixa mapeado no projeto.** Busca no repositório não
   encontrou nenhum dataset, seed, fixture ou documento de um imóvel real
   (`file_search` por `.pdf` → nenhum arquivo; por `imovel` → nenhum arquivo de dados;
   não existe diretório `storage/`, `data/`, `samples/` ou `fixtures/`).
2. **Não há documentos reais** (edital, matrícula em PDF, complementares). Zero PDFs
   no repositório.
3. **PostgreSQL/pgvector indisponível.** Sonda direta de conexão retornou
   `DB_CONNECT=fail: OperationalError` em `127.0.0.1:5432`. Docker/compose não estão
   instalados no ambiente (`docker`, `docker-compose`, `podman` ausentes do PATH).
   Sem banco, nenhuma persistência do fluxo roda.
4. **Sem credencial de LLM.** Não há `.env`; `OPENAI_API_KEY` e `LLM_API_KEY` não
   estão definidos no ambiente. O provider OpenAI é o único suportado por
   `build_gateway()`. A task proíbe criar novo provider/integração/infra, então o
   caminho de LLM real permanece bloqueado por definição.

Consequência: o "primeiro E2E real" fica **bloqueado na etapa 0 (entrada de dados
reais)**, antes mesmo do pipeline documental. As observações abaixo sobre pipeline,
extração, RAG, Agents, LangGraph, Checklist, Risk e Verdict derivam de **leitura do
código real** (contratos e caminhos de execução), não de uma execução com dados
reais — e estão marcadas como tal para não transformar hipótese em fato.

---

## 1. Imóvel utilizado

**Nenhum.** Não existe imóvel real da Caixa mapeado no projeto. A task pressupõe "1
imóvel REAL da Caixa já mapeado pelo projeto"; esse insumo não está presente no
repositório. Nenhum imóvel foi inventado (a instrução explícita é não inventar dados
do imóvel).

## 2. Documentos utilizados

**Nenhum.** Não há edital, matrícula em PDF nem documentos complementares reais no
repositório (0 PDFs). O layout esperado em `storage/property-{id}/original|normalized|metadata`
(descrito na SPEC) não existe fisicamente.

## 3. Fluxo executado

Sequência esperada: Imóvel → Dados do leilão → Edital → Matrícula (PDF) → Demais
documentos → Pipeline documental → Extração → RAG → Agents → LangGraph → Checklist
Mestre → Risk Engine → Verdict Engine → Dossiê final.

**Executado de fato:** apenas o diagnóstico de pré-condições (existência de imóvel,
documentos, banco e LLM). O pipeline não foi iniciado por ausência de entradas reais
e de banco.

## 4. Etapas que funcionaram

- **Diagnóstico de ambiente** (esta task): verificação objetiva de que faltam
  imóvel, documentos, banco e LLM.
- **Coleta e importação da suíte de testes** continua saudável (contexto da Task 50):
  a aplicação FastAPI importa sem erro; os testes de integração coletam e pulam
  corretamente sem banco.

Nenhuma etapa do fluxo E2E de negócio (documental → veredito) foi confirmada
funcionando com dados reais, porque não houve execução real.

## 5. Etapas que falharam / ficaram bloqueadas

- **Etapa 0 — Entrada de dados reais:** bloqueada. Sem imóvel/documentos reais.
- **Persistência (todas as etapas):** bloqueada. PostgreSQL indisponível
  (`OperationalError`).
- **Extração / Agents / RAG (embeddings) / consolidação com LLM:** bloqueadas. Sem
  `OPENAI_API_KEY`; provider OpenAI indisponível; criar provider é proibido nesta task.

## 6. Campos ausentes (observado por leitura de contrato — a validar com dado real)

Pontos onde o contrato atual pode não capturar o que um imóvel real da Caixa costuma
trazer. **Hipóteses de leitura de código, não confirmadas com documento real:**

- **Dados do leilão (`AuctionCreate`/`AuctionNotice`):** não há campo para o
  **número do leilão / lote / identificador do site da Caixa**, nem **modalidade**
  (venda direta, 1º/2º leilão online), nem **datas de 1º e 2º leilão simultâneas**
  (o modelo tem `auction_date` único). A SPEC menciona "dois leilões do art. 27";
  o contrato atual guarda um estágio/uma data por registro.
- **Matrícula (`RegistrationExtraction`/`PropertyRegistration`):** não há campo
  estruturado para **averbações/AV-n** individuais nem para **ônus/consolidação**
  como itens discretos — hoje cabem em `observations` (texto livre), o que dificulta
  rastreabilidade fina exigida pelo Checklist (ex.: "leilões negativos averbados").
- **Edital (`NoticeExtraction`/`AuctionNotice`):** não há campos para
  **responsabilidade por débitos (IPTU/condomínio)**, **cláusula de evicção** ou
  **desocupação**, que são justamente perguntas do Checklist Mestre.

> Estes itens precisam ser confirmados contra um edital/matrícula reais antes de
> virar requisito. Não são, aqui, afirmações definitivas.

## 7. Problemas de extração (observado por leitura de código)

- `extract_document` depende de LLM estruturado (`structured_chat`) e de RAG
  (`RAGService.retrieve_context`). **Sem LLM, a extração não produz saída válida**
  (o teste unitário `test_extraction` já falha na ausência do provider — ver Task 50).
- `DocumentNormalizer` é o componente que transforma PDF em markdown; seu
  comportamento com **PDF real da Caixa** (layout, OCR, tabelas) **não foi validado**
  — nenhum PDF real foi processado. É o primeiro ponto a exercitar quando houver
  documento real.
- Extração só suporta `MATRICULA` e `EDITAL` (`DocumentType`). Documentos
  complementares reais (ex.: laudo, certidões) **não têm caminho de extração
  estruturada** — entram apenas como documento/versão + chunks para RAG.

## 8. Problemas de rastreabilidade (observado por leitura de código)

- A rastreabilidade referência→evidência exige `references` com `chunk_id`/`page`
  válidos (`validate_extraction_references`). Isso depende diretamente da qualidade
  da extração/normalização do PDF real — **não verificável sem documento real**.
- Como averbações e cláusulas do edital hoje caem em texto livre (`observations`),
  a ligação evidência→item do Checklist para perguntas específicas
  (ex.: "consolidação registrada", "leilões negativos averbados") pode ficar frágil.
  **A confirmar com dado real.**

## 9. Problemas de RAG (observado por leitura de código)

- `RAGService` usa embeddings via `gateway.embed(...)` (OpenAI). **Sem
  `OPENAI_API_KEY`, os chunks de um documento novo não recebem embedding** no
  ingest (o pipeline grava chunk com `embedding=None`), e a recuperação semântica
  fica degradada/indisponível. A busca textual (portuguese) ainda existiria, mas o
  ranking híbrido perde o componente vetorial.
- Não foi possível medir recall/precisão de recuperação — sem banco e sem documento
  real, não há o que recuperar.

## 10. Problemas dos Agents (observado por leitura de código)

- Todos os Agents (`Document/Legal/Financial/Market/Checklist`) chamam
  `build_gateway()` e `structured_chat`. **Sem LLM**, cada um retorna `LLMCall` com
  status `SEM_CHAVE`/`ERRO`; o fluxo persiste a tentativa (rastreável) mas **não
  produz findings** reais. Ou seja: sem LLM, os Agents "rodam" mas entregam vazio —
  isso **não deve ser lido como sucesso**.

## 11. Problemas do LangGraph (observado por leitura de código)

- O grafo `LOAD_CONTEXT → RETRIEVE_RAG → RUN_AGENTS → CONSOLIDATE` está íntegro
  (validado por testes unitários existentes, Task 26/27). Ele **executa** mesmo com
  Agents sem LLM, apenas consolidando resultados vazios. Nenhum problema estrutural
  observado; a limitação é de **conteúdo** (agents vazios), não de topologia.

## 12. Problemas do Checklist (observado por leitura de código)

- O Checklist Mestre é semeado no cadastro do imóvel e recebe resultados via
  `persist_agent_findings`/`persist_checklist_agent_findings`. Sem findings dos
  Agents (bloqueio de LLM), os itens permanecem em `PENDENTE` — **não é possível
  confirmar, com dados reais, se as evidências chegam corretamente ao Checklist**.
  Este é um dos objetivos centrais da task que fica **não verificado**.

## 13. Problemas de Risk/Verdict (observado por leitura de código)

- `RiskEngine` e `VerdictEngine` são determinísticos e independem de LLM; foram
  validados por testes unitários (Tasks 31/32) e pelos testes de integração da
  Task 50 (que rodam contra banco). Com um checklist vazio (sem findings), o
  veredito tende a `PENDENTE` com itens em aberto — comportamento esperado, **mas
  não exercitado aqui com dado real**.

## 14. Bloqueios por LLM / API / configuração

- **LLM:** sem `OPENAI_API_KEY`/`LLM_API_KEY`; sem `.env`. Provider OpenAI é o único
  suportado. **Bloqueio registrado; não mascarado.** Não foi criado provider/mocked
  para fingir execução de LLM.
- **Banco:** PostgreSQL/pgvector indisponível (`OperationalError` na porta 5432;
  Docker ausente). Sem banco, o fluxo não persiste.
- **Dados:** sem imóvel real e sem documentos reais no projeto.

## 15. Lista objetiva de correções necessárias para as próximas tasks

Ordenada por dependência (o primeiro item é pré-requisito de tudo):

1. **Prover as entradas reais do E2E** (fora do escopo desta task diagnóstica):
   - definir e versionar **1 imóvel real da Caixa** (dados do anúncio/leilão);
   - disponibilizar **edital real (PDF)**, **matrícula real (PDF)** e demais
     documentos, em local acessível ao pipeline (`storage/` ou fixture de teste).
2. **Disponibilizar runtime de execução do E2E:**
   - subir PostgreSQL/pgvector (docker-compose já existe no repo) e aplicar migrations;
   - fornecer `OPENAI_API_KEY` (ou definir explicitamente um modo de execução
     sem-LLM que seja honesto, sem inventar findings).
3. **Validar `DocumentNormalizer` com PDF real da Caixa** (layout/tabelas/averbações)
   — provável primeiro ponto de quebra do pipeline documental real.
4. **Revisar o contrato de dados do leilão** para suportar identificador/lote da
   Caixa, modalidade e **datas dos dois leilões** (art. 27) — confirmar contra edital
   real antes de alterar.
5. **Revisar o contrato de matrícula/edital** para estruturar averbações,
   consolidação, ônus e responsabilidades por débitos/evicção/desocupação, que hoje
   caem em texto livre e enfraquecem a rastreabilidade evidência→Checklist —
   confirmar contra documentos reais antes de alterar.
6. **Definir tratamento de documentos complementares** além de MATRICULA/EDITAL no
   caminho de extração estruturada (hoje só entram como chunks para RAG).
7. **Medir RAG com documento real** (recall/ranking híbrido) uma vez que embeddings
   estejam disponíveis.

> Nenhuma das correções acima foi implementada nesta task (task diagnóstica). Cada
> alteração de contrato deve ser confirmada contra um documento real antes de virar
> requisito, para não introduzir campos inventados.

---

## Notas de método (o que foi e o que não foi feito)

- Não foi criado imóvel, documento, provider de LLM, endpoint, Agent, regra de
  negócio ou infraestrutura.
- Não se alterou LangGraph, Risk Engine, Verdict Engine, RAG ou motores financeiros.
- Não se mascarou a ausência de LLM/banco/dados como execução bem-sucedida.
- Observações sobre etapas internas (extração/RAG/Agents/checklist) foram derivadas
  de leitura do código e marcadas como **a confirmar com dado real**, sem transformar
  hipótese em fato.

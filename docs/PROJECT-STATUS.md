# Radar Leilão — Controle Central do Projeto

> Documento operacional central do desenvolvimento.  
> Última consolidação: 21/09/2026  
> Branch principal: `main`  
> Repositório: `jabesfelipe/radar-leilao`

## 1. Objetivo

O Radar Leilão é um MVP local-first para análise rastreável de imóveis em **leilões extrajudiciais**, com imóvel como entidade central, documentos/evidências como fonte de verdade, análise incremental, histórico e memória estruturada.

A especificação arquitetural oficial permanece em:

- `SPEC-VIBE-CODING-RADAR-LEILAO.md`

Este documento não substitui a SPEC. Ele controla o **andamento de implementação**, registra o que já foi validado e aponta a próxima tarefa.

---

## 2. Regra de desenvolvimento

Fluxo oficial a partir deste documento:

1. Kiro lê este arquivo.
2. Kiro executa **somente a próxima TASK marcada como PENDENTE**.
3. Kiro implementa e cria commit.
4. Usuário informa: **"da pull"**.
5. O assistente consulta o GitHub, compara o commit com o último estado aprovado e revisa o código alterado.
6. Se houver problema, é criada correção antes de avançar.
7. Se estiver correto, a TASK recebe **[x] CONCLUÍDA** neste documento.
8. O próximo item pendente vira a próxima instrução operacional para o Kiro.
9. Cada avanço de tarefa deve deixar um commit rastreável.

### Critério de aprovação

Uma TASK só é considerada concluída quando:

- o código implementa o escopo solicitado;
- não inventa regra de negócio;
- não cria enum/regra/campo não suportado pela SPEC ou contrato existente;
- testes/build relevantes passam;
- não há regressão evidente;
- o escopo negativo da TASK foi respeitado;
- o commit é identificável.

---

## 3. Estado atual

**Último commit implementado:** `30f366678b9359238cdca08d5a5724acacf6a9076f`  
**Mensagem:** `feat: implementa financeiro no hub do imovel`

**Última TASK aprovada:** TASK 43

**Próxima TASK:** TASK 44 — Mercado + Ocupação no Hub do Imóvel

**Status global:** 🟡 MVP em construção

> A porcentagem de conclusão não é usada como fonte oficial. O controle por TASK abaixo é a referência.

---

# 4. Backlog controlado

## Fundação, arquitetura e IA

- [x] **TASK 01** — Implementar MVP inicial do Radar Leilão em português.
  - Commit: `d984909c9354e4472c999e5820fb0871064f309d`

- [x] **TASK 02** — Alinhar arquitetura do Radar à SPEC oficial.
  - Commit: `1be818451b38cf5b691f0fc0707a6e2610a40005`

- [x] **TASK 03** — Implementar primeira análise real com LLM, RAG e LangGraph.
  - Commit: `db5e488b2bfe3906f42d285553e84a4438993acc`

- [x] **TASK 04** — Estabilizar RAG híbrido com isolamento e ranking normalizado.
  - Commit: `f7bad52fe9c6d5613f39a44cf90ac9941087dc0d`

- [x] **TASK 05** — Adicionar rastreabilidade e controle de custos de LLM.
  - Commit: `7218b87f0c8a4122c998c88c36cd9e9fec3d4db5`

- [x] **TASK 06** — Endurecer segurança do fluxo LLM.
  - Commit: `f39fb619e0bb9c36bb5ecd5bb8c721ec4335b7a1`

- [x] **TASK 07** — Implementar Checklist Mestre versionado.
  - Commit: `5261c6c84c3ee346d8e1e4974bc9342572820e3b`

- [x] **TASK 08** — Implementar motor financeiro determinístico.
  - Commit: `df8c11ba7571714684c4582bfbc4a43ffa1eaf79a`

- [x] **TASK 09** — Implementar motor determinístico de mercado.
  - Commit: `04333e888a432a57559a5853b33ebaa930a34067`

- [x] **TASK 10** — Adicionar cadastro de ocupação do imóvel.
  - Commit: `5300ab6b35df859deca08d5a5724acacf6a9076f`

- [x] **TASK 11** — Adicionar cadastro de processos jurídicos.
  - Commit: `0fd36e1a8011aae819d539c91cd20f5d5fa90ea6`

- [x] **TASK 12** — Adicionar versionamento de documentos.
  - Commit: `d3b1d69c088359577ea5a3ca5f76d8872d3cbbcd`

- [x] **TASK 13** — Consolidar custos e dívidas do imóvel.
  - Commit: `ad81ad0f90f3a190b51b173aa81239a20dea8059`

- [x] **TASK 14** — Adicionar cadastro de matrícula e edital.
  - Commit: `1fc9dba87d68d7c6649df2e55ca5f75a82219e70`

- [x] **TASK 15** — Consolidar evidências e vínculos.
  - Commit: `080cdd8d1059ccfde1f70d9b23086c05c71c7635`

- [x] **TASK 16** — Consolidar pipeline documental para RAG.
  - Commit: `ad55db96b817e5858077d09eb675a492fc29105e`

- [x] **TASK 17** — Adicionar extração documental estruturada.
  - Commit: `5672cbc08436b1365820723ed261ab2584266f0e`

- [x] **TASK 18** — Exigir rastreabilidade na extração documental.
  - Commit: `4f54f07a92ff58ddde214038504609b2e686c817`

- [x] **TASK 19** — Normalizar evidências documentais.
  - Commit: `db12b25704f8deb29e5adbda933b4c16319b3411`

- [x] **TASK 20** — Adicionar endpoint do Document Agent.
  - Commit: `95a28afeb84f55c0a6b2678e8191c7f1476f6f32`

- [x] **TASK 21** — Ajustar rastreabilidade do Document Agent.
  - Commit: `32ca1957abbfe35ffa7a1752696c6fbc1c8beb58`

- [x] **TASK 22** — Adicionar Jurídico Agent.
  - Commit: `060b6a6a89715695262df4dc5f99f18de82f68bf`

- [x] **TASK 23** — Adicionar Financeiro Agent.
  - Commit: `5f7ee44826468ff87930db9c79a5cf96c8d5fe30`

- [x] **TASK 24** — Adicionar Mercado Agent.
  - Commit: `f3b71965c6dd7e6e0ab7c54709c91088629d60b3`

- [x] **TASK 25** — Adicionar Checklist Agent.
  - Commit: `118dbf463f99aff3a2f558502eb9df0edb6f6514`

- [x] **TASK 26** — Consolidar orquestração com LangGraph.
  - Commit: `3971ba926f96f82cb4763957c0fa7d8156cc18a3`

- [x] **TASK 27** — Separar consolidação de Risk e Verdict no LangGraph.
  - Commit: `5d91b8e4bbfc2c5bab02c310151440c65b1476b7`

- [x] **TASK 28** — Adicionar Impact Analyzer determinístico.
  - Commit: `d659aef262b428bf5f1d5320dd0aa56721e0ac5a`

- [x] **TASK 29** — Implementar reanálise incremental.
  - Commit: `3f87a76bce36f4cd123b8455328fa1d9be446356`
  - Correção obrigatória posterior:
    `d416345516fe11c7c27a1684a4071d916433dfaf`
  - A correção limitou a criação do ChecklistExecution aos casos em que checklist está realmente afetado.

- [x] **TASK 30** — Adicionar consolidação dos resultados dos Agents.
  - Commit: `b76c77311b60d082d169397cdab8bbf412a8d14a`

- [x] **TASK 31** — Implementar Risk Engine determinístico.
  - Commit inicial: `023bb2856fd67ce168b9137e18e3a506f8780f61`
  - Correção aprovada: `acc515f321a6f827ae32c10be98972940530fe08`
  - A correção removeu regras de risco que não estavam formalizadas.

- [x] **TASK 32** — Implementar Verdict Engine determinístico.
  - Commit: `12b2914abe3fe672c4fed1b27f2da4d5b444aeb3`

- [x] **TASK 33** — Implementar comparação de histórico de análises.
  - Commit: `37386bb47b246252ebdc0ba595b90b5d953c8910`

- [x] **TASK 34** — Adicionar memória estruturada de casos.
  - Commit: `f7d951ac3ebdcec98e4524e6d8152b9e124e2d40`

- [x] **TASK 35** — Adicionar busca estruturada da memória.
  - Commit: `1c5f95ca9b287eb1487fc58a5f95117729dd4075`

- [x] **TASK 36** — Adicionar embeddings na memória de casos.
  - Commit: `e4e9f394c599df4661f96084ec2c8b16e185d113`

- [x] **TASK 37** — Adicionar busca semântica da memória.
  - Commit: `e5572d3cfaa0123eaa1ad0dace196e9b400d2380`

- [x] **TASK 38** — Adicionar busca híbrida da memória.
  - Commit: `9636f93c61e10e2702176ef882f1894a54bf6550`

- [x] **TASK 39** — Adicionar evals básicos dos Agents.
  - Commit: `64b156ef60c662071709ef8970d2bc20f8f361da`

## Frontend e Hub do Imóvel

- [x] **TASK 40** — Criar foundation do frontend.
  - Commit: `e8f8a9a7172220c3ed90430c9a3aac34e1a1edf0`

- [x] **TASK 40A** — Reforçar responsividade do frontend.
  - Commit: `4d248c724ab53d4347bf5ffcddc2c7769b40f0ed`

- [x] **TASK 40B** — Criar identidade visual e design system do Radar.
  - Commit: `392f9b677f6bc73cb19c7769d32403d225e1b962`

- [x] **TASK 41** — Cadastro básico de imóvel.
  - Commit inicial: `0c10233c0a8b379e22a39c40050e5377533aa435`
  - Correção aprovada: `d244a08e375e4b2c23f88e9acbeccd84fe12719b`
  - Correção removeu enum artificial de tipo de imóvel.

- [x] **TASK 42** — Criar Hub de Detalhe do Imóvel.
  - Commit: `c7c9ac51de790282bd65b32f3c94c4dc8eb0f43f`

- [x] **TASK 42A** — Implementar Documentos no Hub.
  - Commit: `147e8bc5cd8e7a10dfcb95a6a95c12e05f101f08`

- [x] **TASK 42B** — Implementar Matrícula e Edital no Hub.
  - Commit: `1c330c430793bf2da50ed462ef16f34aff24da38`

- [x] **TASK 42C** — Implementar Processos Jurídicos no Hub.
  - Commit: `a4f5d761167cccda07e233816af05cda449b0e73`

- [x] **TASK 43** — Implementar Financeiro no Hub.
  - Commit: `30f366678b9359238cdca08d5a5724acacf6a9076f`

> Observação: TASKs A/B/C foram refinamentos do plano operacional original. Elas são mantidas aqui para preservar o histórico real dos commits sem alterar artificialmente a sequência principal.

---

# 5. PRÓXIMA TASK — PENDENTE

## TASK 44 — Mercado + Ocupação no Hub do Imóvel

**Status: [ ] PENDENTE**

### Objetivo

Implementar somente o frontend de cadastro e visualização dos dados já suportados pelo backend.

### Regras obrigatórias

Antes de implementar:

- inspecionar os endpoints existentes;
- usar exatamente os contratos atuais;
- não alterar backend;
- não alterar models;
- não criar migration;
- não criar regra de negócio;
- não chamar LLM/RAG/Agents.

### Mercado

Usar exatamente o contrato `ComparableCreate`:

- `kind`
- `price`
- `rent`
- `area_m2`
- `source`
- `url`

Implementar:

- listagem;
- botão Novo comparável;
- cadastro;
- loading;
- empty state;
- erro;
- retry;
- saving;
- sucesso;
- integração no Hub.

**Não implementar:** média de preço, preço/m², valuation, liquidez, yield, ranking, score ou veredito.

Não criar enum artificial para `kind`; o contrato atual é string.

### Ocupação

Usar exatamente o contrato `OccupancyCreate`:

- `status`
- `occupant_profile`
- `estimated_cost`
- `estimated_months`
- `evidence_id`

Status válidos do contrato atual:

- `OCUPADO`
- `DESOCUPADO`
- `DESCONHECIDO`

Implementar visualização e cadastro/atualização **somente conforme os endpoints existentes**.

**Não assumir endpoint de update:** primeiro verificar o backend. Se houver apenas criação, implementar o fluxo suportado pelo contrato atual, sem inventar PUT/PATCH.

Não fazer interpretação jurídica ou financeira.

### Hub

Substituir os placeholders de:

- Mercado
- Ocupação

### Testes

Mercado:

- loading;
- empty;
- list;
- create;
- error;
- retry;
- integração no Hub.

Ocupação:

- loading;
- empty;
- dado existente;
- create/update conforme endpoint real;
- error;
- retry;
- integração no Hub.

### Responsividade

Obrigatória:

- desktop;
- tablet;
- mobile;
- responsive-first;
- formulários em uma coluna quando necessário;
- botões com área de toque adequada;
- sem scroll horizontal da página;
- textos legíveis;
- navegação mobile existente preservada.

### Escopo negativo

Não implementar nesta TASK:

- valuation;
- preço/m²;
- médias;
- liquidez;
- yield;
- ROI;
- risco;
- veredito;
- LLM;
- RAG;
- Agents;
- novas regras de negócio.

### Commit esperado

`feat: implementa mercado e ocupacao no hub do imovel`

---

# 6. Backlog futuro

Depois da TASK 44, continuar nesta ordem, refinando cada item somente quando chegar sua vez:

- [ ] **TASK 45** — Checklist no Hub do Imóvel
- [ ] **TASK 46** — Riscos + Veredito no Hub
- [ ] **TASK 47** — Histórico no Hub
- [ ] **TASK 48** — Fluxo completo de análise do imóvel
- [ ] **TASK 49** — Revisão de integração Frontend ↔ Backend
- [ ] **TASK 50** — Testes de integração
- [ ] **TASK 51** — Primeiro teste end-to-end com imóvel real da Caixa
- [ ] **TASK 52** — Correções encontradas no teste real
- [ ] **TASK 53** — Hardening do MVP
- [ ] **TASK 54** — Revisão final contra a SPEC
- [ ] **TASK 55** — Preparação/release do MVP

As descrições detalhadas dessas TASKs serão definidas **somente quando a TASK anterior for aprovada**, evitando planejamento excessivo e gasto desnecessário de tokens.

---

# 7. Áreas já construídas

## Backend / domínio

- Imóvel
- Leilão
- Documentos e versões
- Matrícula
- Edital
- Processos jurídicos
- Custos
- Dívidas
- Mercado
- Ocupação
- Evidências
- Checklist Mestre
- Histórico de análises
- Riscos
- Veredito
- Memória de casos

## IA

- LLM Gateway
- RAG híbrido
- embeddings
- busca semântica
- busca estruturada
- memória híbrida
- Document Agent
- Jurídico Agent
- Financeiro Agent
- Mercado Agent
- Checklist Agent
- LangGraph
- Impact Analyzer
- reanálise incremental
- consolidação de resultados
- Risk Engine determinístico
- Verdict Engine determinístico
- evals básicos

## Frontend

- foundation React + TypeScript + Vite
- responsividade
- design system
- identidade visual
- cadastro de imóvel
- Hub de detalhe
- Documentos
- Matrícula
- Edital
- Processos Jurídicos
- Financeiro

---

# 8. Regras de produto que não devem ser inventadas

1. O produto é focado no MVP em leilões extrajudiciais.
2. O imóvel é a entidade central.
3. A evidência deve ser rastreável.
4. Documento original deve permanecer preservado.
5. A análise deve preservar histórico.
6. Mudanças relevantes devem permitir reanálise incremental.
7. Cálculos financeiros determinísticos não devem ser terceirizados ao LLM.
8. Risk e Verdict devem seguir regras formalizadas.
9. Não criar regras de negócio apenas porque parecem razoáveis.
10. Não inventar enums quando o contrato é string.
11. Não alterar backend durante TASKs explicitamente frontend-only.
12. Não usar LLM/RAG/Agents em tarefas que não pedem isso.
13. Não duplicar o Checklist Mestre por domínio.
14. A contagem final do checklist deve vir da matriz canônica real, nunca de estimativa.
15. Legal/jurisprudência deve ser tratado com evidência e verificação atual quando o módulo chegar à fase correspondente.

---

# 9. Controle de auditoria

Quando o usuário disser **"da pull"**:

1. Buscar o commit mais recente do repositório.
2. Comparar com o último commit aprovado.
3. Listar arquivos alterados.
4. Ler o código alterado.
5. Conferir escopo positivo.
6. Conferir escopo negativo.
7. Conferir contratos existentes.
8. Conferir testes/build quando evidenciados pelo commit.
9. Classificar:
   - 🟢 aprovado;
   - 🟡 aprovado com observação;
   - 🔴 correção necessária.
10. Só após aprovação, atualizar este documento marcando a TASK como concluída e definindo a próxima.
11. Fazer commit/push da atualização documental.

---

# 10. Fonte de verdade

Em caso de conflito:

1. código e contratos reais do repositório;
2. `SPEC-VIBE-CODING-RADAR-LEILAO.md`;
3. este controle de andamento;
4. descrição operacional da TASK.

Este arquivo serve para **controle e continuidade**, não para substituir a implementação nem a SPEC.

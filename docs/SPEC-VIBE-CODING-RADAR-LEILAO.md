# RADAR LEILÃO — ARQUITETURA MESTRA

**Versão:** 4.0 — Business + Arquitetura + Implementação + Encerramento do MVP  
**Status:** Documento mestre oficial e registro final do MVP encerrado  
**Idioma:** Português do Brasil (pt-BR)  
**Idioma do sistema:** Português do Brasil (pt-BR)  
**Escopo:** Leilões extrajudiciais de imóveis no Brasil

---

# 1. Objetivo

O Radar Leilão é uma plataforma de inteligência para análise de imóveis em leilões extrajudiciais.

O sistema deve transformar informações estruturadas, documentos, registros, processos, dados financeiros e informações de mercado em um **dossiê vivo, rastreável e versionado** do imóvel.

O Radar não deve ser apenas um chatbot ou um analisador de PDF.

Ele deve funcionar como um sistema de conhecimento acumulativo:

```text
IMÓVEL
  ↓
DOCUMENTOS + DADOS + PESQUISAS
  ↓
NORMALIZAÇÃO
  ↓
CONHECIMENTO
  ↓
ANÁLISES ESPECIALIZADAS
  ↓
CHECKLIST
  ↓
RISCOS
  ↓
VEREDITO
  ↓
HISTÓRICO
  ↓
MEMÓRIA DO RADAR
  ↓
PRÓXIMAS ANÁLISES
```

---

# 2. BUSINESS CANÔNICO — MÉTODO DO RADAR

Esta seção é a referência funcional do produto. A arquitetura técnica deve existir para implementar este business, e não o contrário.

## 2.1 Objetivo do negócio

O Radar deve permitir analisar um imóvel de leilão extrajudicial de ponta a ponta, começando com informações incompletas e enriquecendo o dossiê ao longo do tempo.

O usuário pode:

1. cadastrar o imóvel;
2. informar os dados do leilão;
3. anexar documentos;
4. analisar matrícula e edital;
5. pesquisar processos;
6. inserir processos encontrados posteriormente;
7. inserir débitos;
8. inserir custos;
9. inserir orçamento de reforma;
10. inserir comparáveis de mercado;
11. atualizar ocupação;
12. executar/reexecutar análises;
13. acompanhar o checklist;
14. acompanhar riscos;
15. consultar o impacto financeiro;
16. consultar o Veredito;
17. continuar adicionando informações posteriormente.

Cada nova informação deve preservar o histórico e recalcular somente o que foi afetado.

## 2.2 Unidade central do negócio

O imóvel é o centro do dossiê.

```text
IMÓVEL
├── Leilão
├── Documentos
├── Matrículas
├── Editais
├── Processos
├── Débitos
├── Custos
├── Reforma
├── Ocupação
├── Mercado
├── Comparáveis
├── Checklist
├── Evidências
├── Riscos
├── Análises
├── Vereditos
└── Histórico
```

## 2.3 Fluxo de negócio

```text
ENTRADA DO IMÓVEL
        ↓
DADOS DO LEILÃO
        ↓
DOCUMENTOS
        ↓
DUE DILIGENCE
        ↓
┌───────┬─────────┬──────────┬────────────┬─────────────┐
│       │         │          │            │             │
Jurídico Financeiro Mercado Documental Desocupação
│       │         │          │            │
└───────┴─────────┴──────────┴────────────┴─────────────┘
        ↓
CHECKLIST MESTRE
        ↓
RISCOS
        ↓
CENÁRIOS FINANCEIROS
        ↓
VEREDITO
        ↓
HISTÓRICO / MEMÓRIA
```

## 2.4 Princípio de análise progressiva

A análise não precisa estar completa na primeira execução.

Exemplo:

```text
V1 → edital + matrícula
V2 → processo encontrado
V3 → débito de condomínio
V4 → orçamento de reforma
V5 → novos comparáveis
```

Cada versão representa o conhecimento disponível naquele momento.

## 2.5 Entradas posteriores

O sistema deve aceitar novas informações de forma independente:

- processo jurídico pesquisado manualmente;
- movimentação processual;
- débito de condomínio;
- IPTU;
- outro débito;
- custo de reforma;
- orçamento;
- comparável de venda;
- comparável de aluguel;
- informação de ocupação;
- novo edital;
- nova matrícula;
- documento complementar;
- informação cadastral.

## 2.6 Regras de negócio

As regras do Radar devem ser classificadas em:

### Regra determinística

Resultado calculável pelo sistema.

Exemplos:

- custo total;
- desconto;
- preço por m²;
- yield;
- ROI;
- margem;
- preço máximo;
- cenários.

### Regra documental

Depende de evidência documental.

Exemplos:

- existência de averbação;
- consolidação;
- cláusula do edital;
- matrícula da vaga;
- responsabilidade por débitos.

### Regra jurídica

Depende da interpretação de fatos, documentos e fontes jurídicas atuais.

A IA pode auxiliar, mas a conclusão deve ser apresentada com evidências e nível de confiança.

### Regra de mercado

Depende de comparáveis e dados coletados.

### Regra de risco

Transforma uma condição identificada em impacto operacional/financeiro/jurídico.

## 2.7 Classificação dos resultados

O Radar não deve depender de uma resposta binária.

Um item pode estar:

- PENDENTE;
- EM_ANALISE;
- CONFIRMADO;
- RISCO_IDENTIFICADO;
- ATENCAO;
- NAO_IDENTIFICADO;
- NAO_APLICAVEL.

## 2.8 Veredito

O Veredito é uma síntese explicável.

Ele deve responder:

- o que sabemos;
- o que não sabemos;
- quais riscos existem;
- quais evidências sustentam os riscos;
- qual é o impacto financeiro;
- quais pendências ainda precisam ser investigadas;
- o que mudou desde a análise anterior.

O Veredito não deve esconder incerteza.

# 2. Princípios fundamentais

## 2.1 Fonte única de verdade

Este documento é a documentação arquitetural mestre do projeto.

Novas decisões arquiteturais devem ser incorporadas aqui.

Documentações auxiliares podem existir no futuro, mas não devem criar uma arquitetura concorrente.

## 2.2 Tudo em português

A experiência funcional do sistema será em Português do Brasil:

- interface;
- mensagens;
- checklist;
- análises;
- prompts;
- respostas dos agentes;
- relatórios;
- explicações;
- vereditos;
- documentação funcional.

Nomes técnicos de classes, bibliotecas e APIs podem permanecer em inglês quando isso for padrão da tecnologia.

## 2.3 O imóvel é a entidade central

Tudo deve estar relacionado ao imóvel:

```text
IMÓVEL
├── Dados cadastrais
├── Leilão
├── Documentos
├── Matrículas
├── Editais
├── Processos
├── Pesquisas
├── Evidências
├── Checklist
├── Due Diligence
├── Financeiro
├── Mercado
├── Desocupação
├── Riscos
├── Vereditos
└── Histórico
```

## 2.4 Nada importante é sobrescrito

Documentos, evidências, análises e informações externas devem ser versionados.

O sistema deve permitir reconstruir:

- o que era conhecido;
- quando era conhecido;
- qual documento sustentava a informação;
- qual análise foi produzida;
- por que o resultado mudou.

## 2.5 IA interpreta; sistema determina

A LLM não deve ser a autoridade para cálculos ou regras determinísticas.

Exemplos:

- ROI;
- yield;
- custo total;
- preço máximo;
- desconto;
- fórmulas financeiras;
- estados de workflow;
- versionamento;
- integridade de dados.

Essas responsabilidades pertencem ao domínio e aos motores determinísticos.

A IA interpreta documentos, encontra relações, produz hipóteses, classifica evidências e explica resultados.

## 2.6 Toda conclusão importante deve possuir evidência

Uma conclusão deve ser rastreável:

```text
PERGUNTA
  ↓
RESPOSTA
  ↓
EVIDÊNCIA
  ↓
DOCUMENTO
  ↓
VERSÃO
  ↓
PÁGINA / SEÇÃO / ATO
  ↓
INTERPRETAÇÃO
  ↓
RISCO
```

---

# 3. Escopo

## 3.1 Dentro do escopo

- imóveis em leilões extrajudiciais;
- análise de edital;
- análise de matrícula;
- análise documental;
- análise de processos relacionados ao imóvel;
- análise de ocupação;
- análise financeira;
- análise de mercado;
- comparáveis de venda;
- comparáveis de aluguel;
- liquidez;
- custos;
- reforma;
- dívidas;
- condomínio;
- IPTU;
- desocupação;
- checklist extrajudicial;
- histórico;
- memória de análises anteriores;
- atualização incremental;
- RAG;
- agentes de IA;
- evidências;
- versionamento.

## 3.2 Fora do escopo atual

**Leilão judicial não faz parte do escopo da V1.**

O sistema deve ser arquitetado de forma extensível para que isso possa ser adicionado futuramente, mas não será implementado agora.

## 3.3 Natureza do MVP

O projeto é um **MVP**, portanto a arquitetura deve ser robusta nos fundamentos, mas simples na operação.

### O MVP NÃO fará inicialmente

- dezenas de microsserviços independentes;
- infraestrutura distribuída desnecessária;
- Knowledge Graph dedicado;
- Vector DB externo;
- automação completa de todas as fontes externas;
- pesquisa jurídica totalmente automática;
- scraping irrestrito;
- treinamento/fine-tuning próprio de LLM;
- execução completa de todos os agentes em toda análise.

### O MVP fará

- cadastro do imóvel e leilão;
- upload e versionamento de documentos;
- MarkItDown/OCR quando necessário;
- análise documental assistida por IA;
- checklist Mestre configurável;
- RAG com PostgreSQL + pgvector;
- análise financeira determinística;
- cadastro/importação manual de processos e débitos;
- análise de mercado baseada em dados inseridos/pesquisados;
- histórico completo;
- reanálise incremental;
- veredito rastreável;
- frontend em formato semelhante à planilha;
- memória/casos históricos básicos.

---

# 4. Conceito de dossiê vivo

O imóvel não é analisado uma única vez.

Exemplo:

```text
Dia 1
├── Edital
├── Matrícula
└── Dados do leilão

→ Análise V1

Dia 10
├── Nova matrícula
└── Novo processo

→ Análise V2

Dia 20
├── Nova movimentação processual
└── Novo comparável

→ Análise V3
```

O sistema deve conseguir explicar:

```text
VEREDITO V1
      ↓
Nova evidência
      ↓
CHECKLIST afetado
      ↓
Reanálise
      ↓
VEREDITO V2
      ↓
Motivo da mudança
```

---

# 5. Arquitetura geral

```text
                         RADAR LEILÃO
                              │
              ┌───────────────┴───────────────┐
              │                               │
           FRONTEND                         API
        React + TypeScript              Python + FastAPI
              │                               │
              └───────────────┬───────────────┘
                              │
                       DOMAIN / CORE
                              │
       ┌──────────────┬───────┼──────────┬─────────────┐
       │              │       │          │             │
    Imóveis       Checklist  Financeiro  Jurídico   Histórico
       │              │       │          │             │
       └──────────────┴───────┼──────────┴─────────────┘
                              │
                       AI ORCHESTRATOR
                              │
                         LangGraph
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
     Documental            Jurídico           Financeiro
          │                   │                   │
       Mercado            Processos          Desocupação
          │                   │                   │
          └───────────────────┼───────────────────┘
                              │
                         RAG / MEMORY
                              │
             ┌────────────────┼────────────────┐
             │                │                │
          pgvector       Histórico        Memória
             │                │            estruturada
             └────────────────┼────────────────┘
                              │
                       KNOWLEDGE BASE
                              │
                   ┌──────────┴──────────┐
                   │                     │
              DOCUMENTOS             CASOS
                   │                 HISTÓRICOS
                   │                     │
               MarkItDown               │
                   │                     │
             Markdown + OCR              │
                   └──────────┬──────────┘
                              │
                        EVIDÊNCIAS
                              │
                              ▼
                       CHECKLIST ENGINE
                              │
                              ▼
                         RISK ENGINE
                              │
                              ▼
                       VEREDITO ENGINE
                              │
                              ▼
                         HISTÓRICO
                              │
                              └──────► MEMÓRIA
```

---

# 5. DOMÍNIOS FUNCIONAIS DO RADAR

## 5.1 Due Diligence

Orquestra a investigação do imóvel e consolida as informações das demais áreas.

## 5.2 Documentação

Analisa:

- edital;
- matrícula;
- contratos;
- declarações;
- documentos complementares;
- documentos enviados posteriormente.

## 5.3 Jurídico

Analisa:

- matrícula;
- alienação fiduciária;
- consolidação;
- averbações;
- registros;
- ações;
- processos;
- movimentações;
- indisponibilidades;
- penhoras;
- ocupação juridicamente relevante.

Processos podem ser pesquisados externamente e posteriormente inseridos no Radar para nova análise.

## 5.4 Financeiro

Consolida:

- arrematação;
- comissão;
- impostos;
- registro;
- condomínio;
- IPTU;
- débitos;
- reforma;
- desocupação;
- outros custos;
- custo total;
- valor de mercado;
- margem;
- aluguel;
- yield;
- ROI;
- preço máximo;
- cenários.

## 5.5 Mercado

Analisa:

- imóveis similares à venda;
- imóveis similares para aluguel;
- preço;
- preço/m²;
- aluguel;
- aluguel/m²;
- localização;
- estado de conservação;
- características;
- liquidez.

## 5.6 Desocupação

Analisa:

- situação de ocupação;
- evidências;
- perfil da situação;
- complexidade potencial;
- custos;
- prazo potencial;
- impacto no retorno.

## 5.7 Checklist

É a camada de verificação estruturada das regras do método.

## 5.8 Riscos

Consolida riscos:

- jurídicos;
- financeiros;
- documentais;
- de mercado;
- de liquidez;
- de ocupação;
- operacionais.

## 5.9 Histórico

Permite reconstruir a evolução completa do imóvel.

# 6. Frontend

## 6.1 Tecnologia

- React
- TypeScript
- interface em pt-BR

## 6.1.1 Frontend completo no MVP

O frontend do MVP deve contemplar todo o fluxo funcional do business, mesmo que algumas integrações sejam manuais.

A experiência deve permitir:

- cadastrar imóvel;
- cadastrar leilão;
- editar dados;
- anexar documentos;
- visualizar documentos;
- visualizar versões;
- consultar evidências;
- executar análise;
- acompanhar análise;
- consultar checklist;
- ativar/desativar critérios;
- inserir processo;
- inserir movimentação;
- inserir débito;
- inserir custo;
- inserir reforma;
- inserir comparável;
- atualizar ocupação;
- solicitar reanálise;
- visualizar riscos;
- visualizar financeiro;
- visualizar mercado;
- visualizar desocupação;
- visualizar Veredito;
- visualizar histórico;
- comparar versões.

A interface deve ser inspirada na planilha utilizada como modelo mental, sem obrigatoriamente copiar sua implementação visual.

## 6.2 Princípio de UX

O frontend deve seguir a lógica da planilha utilizada como modelo mental do usuário.

Não será um dashboard genérico.

A navegação deve preservar a ideia de abas/guias do método atual.

## 6.3 Estrutura conceitual

```text
┌──────────────────────────────────────────────────────────────┐
│ 🏠 IMÓVEL                                  STATUS             │
│ Endereço | Tipo | Matrícula | Leilão                         │
├──────────────────────────────────────────────────────────────┤
│ VEREDITO │ DUE DILIGENCE │ JURÍDICO │ FINANCEIRO │ ...       │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│                    CONTEÚDO DA ABA                           │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

Guias já definidas no domínio:

- Veredito
- Due Diligence
- Processos Jurídicos
- Financeiro
- Desocupação
- Mercado
- Documentos
- Checklist
- Histórico

A lista definitiva de abas deve respeitar todas as guias existentes na planilha canônica do projeto.

## 6.4 Veredito

O Veredito é uma síntese das áreas analisadas.

Não deve ser um simples:

> comprar / não comprar

Deve apresentar:

- situação de cada área;
- riscos;
- pendências;
- evidências;
- impacto financeiro;
- pontos que precisam de confirmação;
- evolução histórica;
- justificativa.

---

# 7. Backend / domínio

## 7.1 Tecnologia

- Python 3.12+
- FastAPI
- Pydantic
- SQLAlchemy
- Alembic
- PostgreSQL

## 7.2 Entidades principais

### Property

Representa o imóvel.

### Auction

Representa o evento de leilão.

### Document

Documento original recebido pelo sistema.

### DocumentVersion

Versão de um documento.

### Evidence

Evidência extraída ou identificada.

### ChecklistItem

Pergunta/regra do checklist.

### ChecklistExecution

Execução do checklist para determinado imóvel.

### LegalProcess

Processo relacionado ao imóvel.

### ProcessMovement

Movimentação processual.

### MarketComparable

Imóvel comparável.

### FinancialAnalysis

Análise financeira.

### Risk

Risco identificado.

### Analysis

Execução de análise.

### Verdict

Resultado consolidado.

### KnowledgeItem

Conhecimento histórico reutilizável.

### PropertySource

Fonte oficial / link associado ao imóvel (página do imóvel, edital, matrícula, outra). Preserva tipo, URL, descrição e origem para rastreabilidade. Múltiplas fontes por imóvel.

---

## 7.3 Cadastro completo do imóvel (TASK 62)

O cadastro de um imóvel de leilão é um fluxo guiado que reutiliza as entidades acima (nenhum modelo é duplicado) e alimenta diretamente o fluxo de análise existente:

```text
Cadastro de imóvel
   → Dados do imóvel (físicos + identificação na origem)
   → Dados do leilão (avaliação, 1º e 2º leilão, leiloeiro, edital, matrícula)
   → Fontes
   → Documentos
   → Dossiê
   → Análise → Checklist → Riscos → Financeiro → Mercado → Jurídico → Veredito → Histórico
```

Persistência transacional (um único commit) via `POST /api/imoveis/completo`:
`Property` → `Auction` → `AuctionNotice` → `PropertyRegistration` → `PropertySource`.
Documentos e análise de IA são etapas distintas do cadastro (não bloqueiam a criação).

Campos preservados separadamente (o valor de avaliação nunca é sobrescrito pelo valor do leilão):
`Auction.appraisal_value`, `Auction.first_auction_date/value`, `Auction.second_auction_date/value`.
As datas do 1º e 2º leilão são `TIMESTAMP` (data + hora), preservando o horário (ex.: 28/09/2026 10:00) de ponta a ponta (frontend `datetime-local` → API `datetime` → PostgreSQL `timestamp` → dossiê). O upload de documentos é etapa posterior ao cadastro; falhas de upload não desfazem o imóvel e são informadas ao usuário.
Identificação na origem (extensível, sem enum rígido): `Property.origin`, `origin_property_code`, `inscription`, `modality`, `system`.

Caso de validação do primeiro fluxo E2E real: **COND PARQUE ARVOREDO RESIDENCIAL CLUBE** (o E2E real da Caixa não é declarado concluído — apenas o cadastro foi preparado para esse caso).

---

# 8. Documentos

Documentos originais são imutáveis.

Estrutura conceitual:

```text
documents/
└── property-{id}/
    ├── original/
    │   ├── edital.pdf
    │   ├── matricula.pdf
    │   └── outros.pdf
    ├── normalized/
    │   ├── edital.md
    │   ├── matricula.md
    │   └── outros.md
    └── metadata/
        ├── edital.json
        └── matricula.json
```

Cada documento deve possuir:

- identificador;
- nome;
- tipo;
- hash;
- data de entrada;
- origem;
- versão;
- status;
- documento original;
- documento normalizado;
- metadados de extração.

---

# 9. MarkItDown

O Microsoft MarkItDown será utilizado como camada de normalização documental.

Fluxo:

```text
PDF / DOCX / XLSX / imagem
          ↓
      MarkItDown
          ↓
 Markdown estruturado
          ↓
      Chunking
          ↓
     Embeddings
          ↓
      Vector Store
```

Quando necessário:

```text
PDF escaneado
      ↓
OCR
      ↓
Markdown
```

O Markdown é um artefato derivado.

Ele nunca substitui o documento original.

A referência à origem deve ser preservada, permitindo localizar:

- página;
- seção;
- tabela;
- ato;
- trecho.

---

# 10. RAG

O Radar utilizará Hybrid RAG.

Não dependerá exclusivamente de busca vetorial.

```text
                    CONSULTA
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
     Vector Search  Full Text   Metadata
          │            │            │
          └────────────┼────────────┘
                       ▼
                    Rerank
                       ▼
                   Contexto
                       ▼
                     LLM
```

O RAG poderá recuperar:

- documentos;
- evidências;
- casos históricos;
- regras;
- análises anteriores;
- legislação/documentação de referência;
- informações do próprio imóvel.

---

# 11. Memória histórica

A memória é uma característica central do Radar.

O sistema não deve "treinar" novamente o modelo a cada imóvel.

A evolução ocorrerá por meio de memória externa estruturada.

Tipos de conhecimento:

## 11.1 Conhecimento de domínio

- método;
- checklist;
- regras;
- conceitos;
- critérios.

## 11.2 Casos históricos

Experiências obtidas em imóveis já analisados.

## 11.3 Evidências

Informações concretas encontradas em documentos.

## 11.4 Análises anteriores

Resultados produzidos em versões anteriores.

## 11.5 Padrões

Situações recorrentes identificadas no histórico.

Um caso histórico nunca deve ser tratado automaticamente como verdade para outro imóvel.

Ele serve como contexto e evidência de similaridade.

---

# 12. Knowledge Graph

O Knowledge Graph é uma camada evolutiva e não faz parte da implementação do MVP encerrado.

No MVP, as relações entre imóvel, documentos, evidências, processos, análises, checklist, riscos e histórico são persistidas de forma relacional em PostgreSQL e complementadas por pgvector e memória estruturada.

Modelo conceitual:

```text
IMÓVEL
 ├── possui → MATRÍCULA
 │              ├── possui → REGISTRO
 │              └── possui → AVERBAÇÃO
 │
 ├── possui → EDITAL
 │
 ├── relacionado → PROCESSO
 │                    ├── possui → MOVIMENTAÇÃO
 │                    └── possui → DOCUMENTO
 │
 ├── possui → DÍVIDA
 ├── possui → OCUPAÇÃO
 ├── possui → COMPARÁVEIS
 └── possui → ANÁLISES
```

A implementação poderá iniciar de forma relacional e evoluir para uma solução específica caso o volume/complexidade justifique.

---

# 13. LangChain + LangGraph

## 13.1 LangChain

Será utilizado para:

- integração com LLM;
- embeddings;
- retrievers;
- tools;
- prompts;
- parsers;
- pipelines.

## 13.2 LangGraph

Será o orquestrador dos fluxos de análise.

Fluxo principal:

```text
START
  ↓
IDENTIFICAR IMÓVEL
  ↓
ANALISAR DOCUMENTOS
  ↓
┌──────────┬──────────┬──────────┐
Jurídico   Financeiro Mercado
  ↓           ↓          ↓
Processos   Cálculos   Comparáveis
  └───────────┼──────────┘
              ↓
         DESOCUPAÇÃO
              ↓
          CHECKLIST
              ↓
          RISK ENGINE
              ↓
        VEREDITO ENGINE
              ↓
             END
```

---

# 14. Agentes

A arquitetura utilizará agentes especializados.

## Document Agent

Responsável por:

- interpretar documentos;
- identificar fatos;
- extrair entidades;
- localizar evidências;
- apontar páginas/seções.

## Jurídico Agent

Responsável por:

- processos;
- matrícula;
- consolidação;
- registros;
- averbações;
- riscos jurídicos.

## Financeiro Agent

Responsável por:

- interpretar dados financeiros;
- solicitar cálculos ao motor determinístico;
- analisar custo total;
- retorno;
- margem;
- preço máximo.

## Mercado Agent

Responsável por:

- comparáveis;
- venda;
- aluguel;
- liquidez;
- contexto de mercado.

## Desocupação no MVP

Desocupação é um domínio funcional do Radar, mas o MVP encerrado não possui um LLM Agent separado para esse domínio.

A situação de ocupação é representada por dados e análises próprias do domínio e pode alimentar Financeiro, Checklist, Riscos e Veredito.

## Checklist Agent

Responsável por relacionar evidências às perguntas do checklist.

## Supervisor

Coordena os agentes e decide quais etapas precisam ser executadas.

---

# 15. MCP e ferramentas

Agentes devem acessar ferramentas por contratos bem definidos.

Exemplos:

```text
consultar_processos()
consultar_movimentacoes()
buscar_documento()
consultar_matricula()

calcular_tco()
calcular_roi()
calcular_yield()
calcular_preco_maximo()

buscar_comparaveis_venda()
buscar_comparaveis_aluguel()

registrar_evidencia()
executar_checklist()
recalcular_veredito()
```

A IA não deve ter acesso direto e irrestrito ao banco.

---

# 16. Checklist extrajudicial

O checklist será uma estrutura de domínio, e não apenas um documento textual.

Cada item deve possuir:

- ID;
- categoria;
- pergunta;
- tipo de leilão;
- estado;
- resposta;
- confiança;
- evidências;
- fontes;
- interpretação;
- risco;
- última atualização.

Estados:

- PENDENTE
- EM_ANALISE
- CONFIRMADO
- RISCO_IDENTIFICADO
- ATENCAO
- NAO_IDENTIFICADO
- NAO_APLICAVEL

## Perguntas do checklist

1. A intimação para purgar a mora foi pessoal?
2. Se negativa, a intimação foi por edital?
3. Houve envio de notificação para a data dos dois leilões do art. 27 da Lei 9.514/97?
4. O contrato de financiamento com alienação fiduciária em garantia está mais de 80% quitado?
5. O bem dado em garantia é imóvel residencial de pessoa física que garantiu dívida de terceiro?
6. No segundo leilão do art. 27 da Lei 9.514/97, ou em leilões posteriores à consolidação plena da propriedade, o bem está sendo oferecido por menos de 50% do valor de avaliação?
7. Há alguma ação questionando o leilão ou o procedimento de execução extrajudicial antes da data da concorrência?
8. Os leilões negativos do art. 27 da Lei 9.514/97 encontram-se averbados na matrícula?
9. Houve registro do contrato de alienação fiduciária na matrícula? Houve averbação da consolidação da propriedade em nome do credor fiduciário?
10. Os direitos do devedor fiduciante foram penhorados/indisponibilizados?
11. Há um terceiro ocupando o imóvel? Houve contrato de compra e venda entre o devedor fiduciante e um terceiro (cessão de posição contratual)?
12. Há um terceiro que ocupa o imóvel com contrato de locação? O mesmo está registrado na matrícula?
13. O edital do leilão foi lido integralmente?
14. O banco se responsabiliza pela evicção de direito?
15. As responsabilidades sobre os valores em atraso de IPTU e condomínio até a data do leilão estão no edital?
16. A vaga de garagem associada ao apartamento leiloado tem número de matrícula próprio?
17. O imóvel é muito ilíquido, mesmo considerando eventual desconto na venda?
18. A taxa de condomínio é superior a 1% ou 1,5% ao ano em relação ao valor do imóvel ou superior à de imóveis similares na região?
19. É possível achar 7–10 imóveis similares à venda e imóveis similares para aluguel na região?
20. A região é segura/bem servida de serviços públicos e particulares/acesso?
21. O imóvel precisará de grandes obras de manutenção/reforma para se tornar mais líquido?
22. A taxa de retorno esperada está acima da taxa Selic + 15% ao ano?
23. O prazo estimado entre pagamento da arrematação e recebimento do valor total da venda é maior ou igual a dois anos?
24. O imóvel está em cidade/Estado distante do local onde o usuário mora?
25. O imóvel precisará de grandes obras de manutenção/reforma para se tornar mais líquido?
26. Venda sem corretor: o imóvel está em condomínio com portaria?
27. O usuário considera antiético/não se sente à vontade em adquirir imóvel ocupado por uma família?

### Observação jurídica

As perguntas acima representam o método/checklist adotado pelo projeto.

Elas não devem ser tratadas automaticamente como afirmações da legislação vigente.

A análise jurídica deve considerar:

- legislação atual;
- jurisprudência aplicável;
- edital;
- matrícula;
- documentos;
- fatos concretos;
- fontes utilizadas.

---

# 17. Evidências

Cada resposta importante deve apontar para evidências.

Exemplo:

```text
CHECKLIST #09
Resposta: CONFIRMADO

Evidência:
Matrícula 77.677
Versão: 3
Página: 7
Ato: AV-18

Interpretação:
A propriedade foi consolidada em favor do credor.

Confiança:
ALTA

Atualizado:
20/09/2026
```

---

# 17.1 Checklist Mestre extensível
## 17.1.1 Configuração futura

O cadastro de checks deve ser orientado a configuração.

Será possível futuramente:

- criar novo check;
- ativar check;
- desativar check;
- alterar prioridade;
- alterar obrigatoriedade;
- alterar aplicabilidade;
- versionar regra;
- mapear um check para uma regra canônica;
- associar evidências exigidas.

A desativação não elimina execuções antigas.



O checklist do Radar não é limitado aos 27 itens de referência.

A base deve preservar:

- os 27 checks da fonte de referência;
- os checks desenvolvidos durante as análises históricas;
- as regras canônicas normalizadas;
- novos checks futuros.

Checks de origem não devem ser apagados quando houver normalização. Eles devem ser relacionados às regras canônicas.

Cada check poderá ser:

- ATIVO;
- INATIVO;
- OBRIGATÓRIO;
- OPCIONAL;
- NÃO APLICÁVEL.

A desativação nunca apaga histórico.

O cadastro deve permitir ativar, desativar, versionar e substituir critérios sem perder execuções anteriores.

A quantidade final de checks operacionais deve ser determinada pela matriz canônica real do projeto, evitando contar duplicidades como regras independentes.

# 18. Processos jurídicos

Processos são entidades versionadas.

Devem armazenar:

- número;
- tribunal;
- classe;
- partes;
- assunto;
- datas;
- status;
- movimentações;
- documentos;
- fonte;
- data da consulta;
- impacto no imóvel;
- riscos identificados.

Nova movimentação:

```text
PROCESSO
   ↓
NOVA MOVIMENTAÇÃO
   ↓
IDENTIFICAR IMPACTO
   ↓
CHECKLIST AFETADO
   ↓
REANÁLISE
   ↓
NOVO VEREDITO
```

---

# 19. Motor financeiro

O motor financeiro será determinístico.

Conceito:

```text
Arrematação
+ Comissão
+ ITBI
+ Registro
+ Condomínio
+ IPTU
+ Reforma
+ Desocupação
+ Outros custos
---------------------
CUSTO TOTAL
```

A partir disso:

- custo total;
- preço de mercado;
- margem;
- desconto;
- aluguel;
- yield;
- ROI;
- prazo;
- preço máximo;
- cenários.

A LLM pode interpretar o resultado, mas não substituir o cálculo.

---

# 20. Mercado

O sistema deverá trabalhar com comparáveis.

Idealmente:

- 7–10 imóveis similares à venda;
- imóveis similares para aluguel;
- localização;
- metragem;
- quartos;
- vagas;
- condomínio;
- estado de conservação;
- preço;
- preço/m²;
- aluguel;
- aluguel/m²;
- características relevantes.

Os dados devem ser registrados com:

- fonte;
- data da coleta;
- URL/origem;
- características;
- histórico quando disponível.

---

# 21. Desocupação

A desocupação deve ser analisada como uma dimensão própria.

Entradas possíveis:

- imóvel ocupado/desocupado;
- tipo de ocupante;
- evidências documentais;
- informações do edital;
- informações externas;
- custos potenciais;
- prazo potencial;
- impacto financeiro.

A IA não deve afirmar fatos sem evidência.

---

# 22. Risk Engine

O Risk Engine consolida riscos provenientes das áreas:

```text
Jurídico
Financeiro
Mercado
Documental
Desocupação
Liquidez
Operacional
```

Cada risco deve possuir:

- categoria;
- descrição;
- evidência;
- severidade;
- impacto;
- confiança;
- status;
- origem;
- histórico.

---

# 23. Veredito Engine

O Veredito é produzido a partir de:

```text
Checklist
+
Riscos
+
Financeiro
+
Mercado
+
Jurídico
+
Documentação
+
Desocupação
+
Pendências
+
Confiança
```

O sistema deve apresentar a justificativa.

Não deve produzir uma conclusão opaca.

Exemplo:

```text
VEREDITO

Documentação:        OK
Jurídico:             ATENÇÃO
Financeiro:           FAVORÁVEL
Mercado:              OK
Desocupação:          PENDENTE
Liquidez:             ATENÇÃO

Principais fatores:
1. ...
2. ...
3. ...

Pendências:
1. ...
2. ...
```

O usuário deve conseguir navegar da conclusão até a evidência.

---

# 24. Reanálise incremental

Uma das principais estratégias de custo.

Nova informação não deve disparar obrigatoriamente uma análise completa.

Exemplo:

```text
Nova matrícula
      ↓
Impacto jurídico
      ↓
Checklist #8, #9, #10
      ↓
Recalcular riscos
      ↓
Recalcular veredito
```

Outro exemplo:

```text
Novo comparável
      ↓
Mercado
      ↓
Liquidez / valuation
      ↓
Financeiro
      ↓
Veredito
```

Isso reduz:

- tokens;
- latência;
- custo;
- processamento desnecessário.

---

# 25. Histórico de análises

Toda análise terá versão.

```text
Analysis V1
Analysis V2
Analysis V3
...
```

Cada versão deve registrar:

- data;
- modelo utilizado;
- prompt/versionamento quando relevante;
- documentos considerados;
- evidências;
- agentes executados;
- resultados;
- mudanças;
- custo/uso de IA quando disponível.

---

# 26. Aprendizado histórico

O Radar deve utilizar imóveis anteriores como casos históricos.

Fluxo:

```text
IMÓVEL NOVO
    ↓
BUSCAR CASOS SEMELHANTES
    ↓
RECUPERAR EVIDÊNCIAS
    ↓
COMPARAR CONTEXTO
    ↓
ANALISAR IMÓVEL ATUAL
    ↓
REGISTRAR NOVO CASO
```

Importante:

**similaridade não significa verdade.**

Um caso histórico deve ser usado como contexto, não como regra automática.

---

# 27. Avaliação da IA

O sistema deve possuir uma estratégia de avaliação.

Imóveis já analisados podem formar um conjunto de referência.

Testar:

- extração;
- classificação;
- recuperação;
- evidências;
- checklist;
- consistência;
- alucinação;
- precisão;
- regressão entre versões.

Fluxo:

```text
CASOS DE REFERÊNCIA
       ↓
NOVA VERSÃO DA IA
       ↓
EVAL
       ↓
COMPARAÇÃO
       ↓
APROVAÇÃO / AJUSTE
```

Isso permitirá trocar modelos sem perder controle de qualidade.

---

# 28. LLM Gateway

A arquitetura deve ser independente do fornecedor.

```text
                  LLM GATEWAY
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
       OpenAI       Bedrock      Outros
```

A aplicação deve trabalhar com uma interface abstrata.

Assim podemos:

- começar usando uma LLM adequada para os primeiros testes;
- controlar custos;
- trocar modelo;
- utilizar modelos diferentes por tarefa;
- avaliar modelos.

---

# 29. Estratégia de modelos

Nem toda tarefa precisa do maior modelo.

Exemplo conceitual:

```text
Extração simples
→ modelo econômico

Classificação
→ modelo econômico/intermediário

Análise documental complexa
→ modelo mais capaz

Síntese final
→ modelo mais capaz

Embeddings
→ modelo específico de embedding
```

A escolha definitiva dos modelos será feita durante a implementação e os testes.

---

# 30. Controle de tokens e custos

Princípios:

- não reenviar documentos completos desnecessariamente;
- usar chunks;
- usar metadata;
- utilizar cache;
- reutilizar resultados;
- executar agentes apenas quando necessários;
- usar RAG;
- fazer reanálise incremental;
- registrar consumo;
- avaliar custo por análise.

Objetivo:

```text
MAIS CONHECIMENTO
≠
MAIS TOKENS
```

O sistema deve aprender a recuperar apenas o contexto necessário.

---

# 30.1 Histórico e eventos — regra transversal

Histórico é obrigatório em todos os domínios relevantes.

Nenhum dado importante deve ser simplesmente sobrescrito.

Toda alteração relevante deve registrar:

- valor anterior;
- novo valor;
- data/hora;
- origem;
- versão;
- evidência;
- evento causador;
- análise afetada;
- usuário/processo responsável quando aplicável.

O estado atual é uma projeção do histórico.

Exemplo:

```text
DÉBITO V1
   ↓
DÉBITO V2
   ↓
EVENTO
   ↓
FINANCEIRO V3
   ↓
CHECKLIST V3
   ↓
VEREDITO V4
```

# 31. Persistência

## PostgreSQL

Será a fonte principal dos dados estruturados.

Responsabilidades:

- imóveis;
- leilões;
- documentos/metadados;
- versões;
- evidências;
- checklist;
- processos;
- financeiro;
- mercado;
- riscos;
- análises;
- vereditos;
- histórico.

## pgvector

Inicialmente será utilizado para embeddings e busca vetorial.

Essa decisão reduz a complexidade inicial.

Uma solução especializada de Vector DB poderá ser introduzida posteriormente se houver justificativa técnica.

## Storage de documentos

No MVP encerrado, documentos originais e artefatos derivados são armazenados em filesystem persistente do backend, montado por volume Docker.

S3/MinIO permanecem como evolução futura; não são dependências do fluxo principal atual.

## Redis

Redis não faz parte da implementação atual do MVP. Poderá ser introduzido futuramente somente se houver necessidade operacional comprovada.

---

# 32. Segurança

Princípios:

- documentos originais protegidos;
- controle de acesso;
- secrets fora do código;
- logs sem dados sensíveis desnecessários;
- auditoria;
- validação de arquivos;
- isolamento entre documentos;
- proteção das ferramentas utilizadas pelos agentes.

---

# 33. Observabilidade

Devemos conseguir responder:

- qual agente executou;
- qual modelo foi usado;
- quais documentos foram recuperados;
- quais evidências foram utilizadas;
- qual ferramenta foi chamada;
- quanto tempo levou;
- quanto custou;
- por que determinada etapa foi executada;
- por que o veredito mudou.

A observabilidade será especialmente importante para o comportamento dos agentes.

---

# 34. Fluxo completo de um imóvel

```text
1. CADASTRAR IMÓVEL
       ↓
2. INFORMAR DADOS DO LEILÃO
       ↓
3. ENVIAR DOCUMENTOS
       ↓
4. ARMAZENAR ORIGINAIS
       ↓
5. MARKITDOWN / OCR
       ↓
6. NORMALIZAR
       ↓
7. CHUNKING + METADATA
       ↓
8. EMBEDDINGS
       ↓
9. INDEXAR
       ↓
10. IDENTIFICAR EVIDÊNCIAS
       ↓
11. ANALISAR DOMÍNIOS
       ├── Jurídico
       ├── Financeiro
       ├── Mercado
       ├── Documental
       └── Desocupação
       ↓
12. EXECUTAR CHECKLIST
       ↓
13. CALCULAR RISCOS
       ↓
14. CALCULAR RESULTADOS
       ↓
15. GERAR VEREDITO
       ↓
16. REGISTRAR HISTÓRICO
       ↓
17. GERAR CONHECIMENTO REUTILIZÁVEL
```

---

# 35. Atualização de imóvel

```text
NOVO DOCUMENTO / PROCESSO / EVIDÊNCIA
              ↓
          IDENTIFICAR
              ↓
        QUAIS ÁREAS AFETA?
              ↓
       ┌──────┼──────┐
       ▼      ▼      ▼
    Jurídico Fin.  Mercado
       │      │      │
       └──────┼──────┘
              ↓
      CHECKLIST AFETADO
              ↓
         RISK ENGINE
              ↓
       VEREDITO VERSÃO N+1
              ↓
           HISTÓRICO
```

---

# 36. Modelo de dados conceitual

```text
Property
 ├── Auction
 ├── PropertyDocument
 │    └── DocumentVersion
 ├── Evidence
 ├── LegalProcess
 │    └── ProcessMovement
 ├── ChecklistExecution
 │    └── ChecklistResult
 ├── FinancialAnalysis
 ├── MarketComparable
 ├── OccupancyAnalysis
 ├── Risk
 ├── Analysis
 ├── Verdict
 └── KnowledgeItem
```

---

# 37. Princípio de rastreabilidade

Toda cadeia importante deve ser navegável:

```text
VEREDITO
   ↓
RISCO
   ↓
CHECKLIST
   ↓
RESPOSTA
   ↓
EVIDÊNCIA
   ↓
DOCUMENTO
   ↓
VERSÃO
   ↓
PÁGINA / SEÇÃO / ATO
```

Isso é requisito funcional, não apenas uma característica técnica.

---

# 38. Estratégia de implementação — MVP

A implementação será incremental e orientada a valor.

## Fase 1 — Fundação

- monorepo;
- React + TypeScript;
- FastAPI;
- PostgreSQL;
- migrations;
- entidade imóvel;
- leilão;
- histórico/eventos;
- layout baseado na planilha.

## Fase 2 — Documentos

- upload;
- object storage;
- versionamento;
- MarkItDown;
- OCR quando necessário;
- metadata;
- evidências.

## Fase 3 — Checklist

- Checklist Mestre;
- ativação/desativação;
- execução por imóvel;
- evidências;
- histórico;
- regras canônicas.

## Fase 4 — IA/RAG

- gateway de LLM;
- embeddings;
- pgvector;
- retrieval híbrido;
- LangChain;
- LangGraph;
- Document Agent;
- Jurídico Agent;
- Financeiro Agent;
- Mercado Agent;
- Checklist Agent;

## Fase 5 — Financeiro e análise

- custos;
- débitos;
- TCO;
- valuation;
- ROI/yield;
- comparáveis;
- Risk Engine;
- Veredito.

## Fase 6 — Reanálise

- eventos;
- Impact Analyzer;
- reanálise incremental;
- histórico de versões.

## Fase 7 — Teste com imóveis reais

Usar os imóveis já analisados como casos de validação do MVP.

Somente depois da validação:

- ampliar agentes;
- adicionar MCP;
- automatizar fontes externas;
- evoluir Knowledge Graph;
- ampliar infraestrutura.

# 39. Critério de sucesso

O Radar estará cumprindo seu objetivo quando for possível:

1. cadastrar um imóvel;
2. inserir dados do leilão;
3. enviar edital e matrícula;
4. processar os documentos automaticamente;
5. gerar conhecimento estruturado;
6. executar análises especializadas;
7. preencher o checklist;
8. calcular o impacto financeiro;
9. analisar mercado;
10. identificar riscos;
11. produzir um veredito explicável;
12. navegar do veredito até a evidência original;
13. adicionar novas informações posteriormente;
14. atualizar somente as áreas afetadas;
15. manter todo o histórico;
16. utilizar casos anteriores nas próximas análises;
17. medir a qualidade da IA.

---

# 40. Decisões arquiteturais consolidadas

| Decisão | Escolha |
|---|---|
| Escopo | Leilão extrajudicial |
| Idioma | Português do Brasil |
| Frontend | React + TypeScript |
| Backend | Python + FastAPI |
| IA | Python + LangChain + LangGraph |
| Banco principal | PostgreSQL |
| Vetorial inicial | pgvector |
| Documentos | Object Storage local no MVP |
| Normalização | MarkItDown |
| OCR | Pipeline de OCR quando necessário |
| RAG | Hybrid RAG |
| Memória | Base externa estruturada |
| Orquestração | LangGraph |
| Agentes LLM | Documental, Jurídico, Financeiro, Mercado e Checklist + Supervisor |
| Ferramentas/MCP | Extensibilidade futura; não dependência do MVP |
| Histórico | Versionado |
| Evidências | Obrigatórias para conclusões relevantes |
| Cálculos | Determinísticos |
| Veredito | Explicável e rastreável |
| Atualização | Incremental |
| LLM | Abstraída por gateway |
| Knowledge Graph | Evolução futura; não implementado como componente dedicado no MVP |
| Evals | Obrigatórios para evolução da IA |
| Judicial | Fora da V1 |

---

# 41. Regra final da arquitetura

O Radar deve ser pensado como:

> **Um sistema de inteligência imobiliária especializado em leilões extrajudiciais, capaz de transformar documentos, dados, evidências, processos, mercado e histórico em análises rastreáveis e conhecimento acumulativo.**

A IA é uma camada fundamental, mas não é o sistema inteiro.

O sistema combina:

```text
DOMÍNIO
+
DADOS
+
DOCUMENTOS
+
REGRAS
+
CÁLCULOS
+
RAG
+
AGENTES
+
MEMÓRIA
+
EVIDÊNCIAS
+
HISTÓRICO
+
IA
```

O resultado esperado é um Radar que **não apenas analisa imóveis, mas melhora sua capacidade de análise à medida que novos imóveis, documentos e evidências são incorporados.**


---

# 42. Fechamento da arquitetura do MVP

A arquitetura do MVP está considerada **fechada para a fase de implementação e validação do fluxo principal**.

Decisões consolidadas:

```text
Frontend       → React + TypeScript
Backend        → Python + FastAPI
Banco          → PostgreSQL
Vetorial       → pgvector
Storage        → S3/MinIO
Documentos     → MarkItDown + OCR
IA             → LangChain + LangGraph
LLM            → Gateway desacoplado
Histórico      → obrigatório e transversal
Eventos        → obrigatório para mudanças relevantes
Checklist      → Mestre, versionado e configurável
Reanálise      → incremental
Financeiro     → determinístico
Evidências     → rastreáveis
Veredito       → explicável
Idioma         → pt-BR
Escopo         → leilão extrajudicial
```

## Regra de execução

A partir desta versão, novas ideias não devem bloquear a validação do MVP. O código atual possui a suíte automatizada verde e o próximo marco é a validação com imóveis e documentos reais.

Se uma capacidade não for necessária para validar o fluxo principal, ela fica registrada como evolução futura.

O objetivo agora é colocar o Radar funcionando com imóveis reais, validar a arquitetura e evoluir a partir de evidências reais de uso.

**Arquitetura parruda nos fundamentos. MVP na implementação.**


---

# 43. DECISÃO FINAL — MVP ENCERRADO

Esta seção registra o estado final do MVP e substitui os estados intermediários de implementação descritos anteriormente neste documento.

## 43.1 Escopo efetivamente encerrado

O MVP foi encerrado com o escopo de leilões extrajudiciais de imóveis no Brasil.

Fluxo principal validado:

    Cadastro do imóvel
      ↓
    Dados do leilão
      ↓
    Fontes e documentos
      ↓
    Normalização / OCR
      ↓
    Chunks + embeddings
      ↓
    RAG híbrido
      ↓
    Agentes especializados
      ↓
    Consolidação
      ↓
    Checklist Mestre
      ↓
    Risk Engine
      ↓
    Verdict Engine
      ↓
    Histórico / memória

## 43.2 Implementação final

### Frontend
- React 19 + TypeScript + Vite.
- Hubs funcionais para o fluxo principal.
- Cadastro de imóvel/leilão.
- Upload e visualização de documentos.
- Documentos, fontes, processos, financeiro, mercado, ocupação/desocupação, checklist, riscos/veredito e histórico integrados ao dossiê.

### Backend
- Python 3.12+.
- FastAPI.
- Pydantic.
- SQLAlchemy.
- Alembic.
- PostgreSQL + pgvector no ambiente local via Docker/WSL.

### Documentos
- Original preservado.
- Versionamento de Document / DocumentVersion.
- MarkItDown para normalização.
- OCR local-first com Tesseract + Poppler quando necessário.
- Metadata de página/seção/origem preservada.
- Embeddings gerados na ingestão quando provider/chave estão disponíveis.
- Falha de embedding não invalida a ingestão documental.

### IA
O MVP possui cinco agentes LLM especializados:
1. Documental;
2. Jurídico;
3. Financeiro;
4. Mercado;
5. Checklist.

O Supervisor coordena a execução desses agentes no LangGraph.

Não existe um Desocupação Agent separado no MVP encerrado. Desocupação permanece como domínio funcional.

### RAG
- Hybrid RAG com busca vetorial + texto + filtros.
- pgvector como armazenamento vetorial.
- Retrieval direcionado por item para o Checklist.
- Limite de 4 chunks por item e 24 chunks distintos no contexto direcionado.
- Seleção final com diversidade por documento para evitar que uma única fonte monopolize o contexto quando documentos relevantes coexistirem.
- Rastreabilidade dos chunks recuperados por agente/análise.

### Checklist
- Um único Checklist Mestre.
- 27 canonical_key de referência preservados.
- Estados válidos: PENDENTE, EM_ANALISE, CONFIRMADO, RISCO_IDENTIFICADO, ATENCAO, NAO_IDENTIFICADO, NAO_APLICAVEL.
- Versionamento e histórico.
- Novos critérios podem ser adicionados futuramente sem apagar execuções anteriores.

### Financeiro
- Cálculos determinísticos fora da LLM.
- Custos, dívidas, comparáveis, ocupação e demais entradas alimentam o motor financeiro.
- A LLM interpreta resultados, mas não substitui os cálculos determinísticos.

### Histórico e memória
- Análises versionadas.
- Evidências rastreáveis.
- Histórico de entidades/eventos.
- Memória estruturada e híbrida para casos históricos.
- V1–V8 do E2E real de referência preservadas.

## 43.3 Validação final real — imóvel 633

O E2E real de referência utilizado para o fechamento foi o imóvel COND PARQUE ARVOREDO RESIDENCIAL CLUBE, da Caixa, em Curitiba/PR.

Na V8 (analysis_id=280):
- 5/5 agentes concluíram;
- modelo utilizado: gpt-4o-mini;
- 35.231 tokens reportados;
- custo aproximado registrado: US$ 0,0072;
- edital e matrícula coexistiram no contexto dos cinco agentes;
- Checklist: 7 CONFIRMADO / 20 PENDENTE;
- Veredito: INCONCLUSIVO;
- V1–V8 preservadas.

O objetivo do E2E não foi produzir um imóvel aprovado, mas validar o fluxo técnico e o comportamento conservador da análise diante de evidências e lacunas reais.

## 43.4 Correção final de RAG — Task 68

A Task 67 identificou que o edital não chegava ao contexto porque somente a matrícula possuía embeddings.

A Task 68:
- reprocessou controladamente o edital doc 193;
- criou a versão 2 (document_version_id=474);
- gerou 544 chunks com embeddings de dimensão 1536;
- preservou a versão anterior;
- evitou backfill global;
- introduziu diversidade por documento na seleção final do retrieval direcionado;
- adicionou validação defensiva de chunk_id recebido da LLM;
- validou coexistência edital + matrícula.

Resultado no retrieval direcionado do imóvel 633:
- antes: 24 edital / 0 matrícula;
- depois: 22 edital / 2 matrícula.

## 43.5 Testes e evidências de encerramento

A última suíte backend registrada após a Task 68:

    pytest -q
    258 passed

A validação real também confirmou:
- 5 agentes concluídos;
- V1–V8 preservadas;
- 27 canonical_key preservados;
- nenhuma migration introduzida pela Task 68;
- nenhuma confirmação artificial na correção de retrieval;
- documentação de status/histórico atualizada.

O número de testes acima é o resultado da suíte backend registrada no fechamento; não representa, por si só, homologação de produção ou validação jurídica dos resultados.

## 43.6 Limitações conhecidas e backlog

**Follow-up operacional identificado após o fechamento do núcleo:** o serviço de reanálise incremental está implementado em `backend/app/incremental.py` e possui testes unitários, mas o código atual não possui endpoint/worker operacional que invoque `IncrementalAnalysisService.run_for_event()`. O endpoint `POST /api/imoveis/{property_id}/analisar` executa uma nova análise diretamente e não substitui o fluxo incremental baseado em `DomainEvent`.

A **Task 69** fica restrita à criação desse gatilho operacional para permitir a validação real V8 → V9. Ela não altera arquitetura, RAG, agentes, Checklist, ImpactAnalyzer ou o serviço incremental já implementado.


1. Retrieval por item ainda pode favorecer uma fonte semanticamente próxima. Em perguntas muito específicas da matrícula, o chunk da matrícula pode não ocupar o topo do retrieval por item, embora a fonte continue disponível no contexto consolidado.
2. Doc 195 do imóvel 633 permanece sem embedding, por ser duplicata do edital doc 193 reprocessado.
3. Integrações externas continuam podendo ser manuais. O MVP não depende de automação completa de portais externos.
4. MCP externo não é dependência do MVP e permanece como evolução.
5. Knowledge Graph dedicado permanece como evolução.
6. S3/MinIO não são dependências do MVP local; o storage atual usa filesystem persistente.
7. Redis não é utilizado atualmente.
8. Leilões judiciais continuam fora do escopo.
9. A análise de IA não substitui validação jurídica profissional nem decisão de investimento.
11. A reanálise incremental possui serviço e testes, mas aguarda gatilho operacional para validação E2E real V8 → V9.
10. A suíte automatizada verde não equivale a homologação de produção.

## 43.7 Regra para continuidade futura

Se o projeto for retomado por outro desenvolvedor, IDE, agente ou ferramenta de coding, a fonte de contexto deve ser:
1. docs/SPEC-VIBE-CODING-RADAR-LEILAO.md — arquitetura e business canônicos;
2. docs/PROJECT-STATUS.md — estado atual;
3. docs/PROJECT-HISTORY.md — decisões e evolução;
4. código atual e testes — comportamento efetivamente implementado.

Nenhuma ferramenta externa deve ser considerada fonte de verdade quando divergir do código e desta documentação.

## 43.8 Declaração de encerramento

**MVP ENCERRADO — núcleo funcional.**

O núcleo funcional previsto para o MVP foi implementado e validado pelo conjunto de testes automatizados e pelo E2E real de referência descrito acima.

A partir deste ponto, novas capacidades devem ser tratadas como evolução/backlog. A única exceção imediata é a **Task 69**, que não adiciona capacidade funcional nova: apenas expõe operacionalmente o serviço de reanálise incremental já implementado para permitir a validação V8 → V9.

Após a validação da Task 69, o próximo marco será o E2E de um imóvel novo do zero.


---

# 44. ADDENDUM — Validação real pela UI e Task 70

Esta seção registra decisões posteriores ao fechamento do núcleo funcional do MVP e tem precedência sobre qualquer descrição anterior que conflite com o estado atual de validação.

## 44.1 Princípio de UX para evidências

**IDs internos de banco não são uma interface adequada para o usuário final.**

A rastreabilidade técnica deve permanecer, mas a apresentação deve transformar a evidência em uma referência compreensível.

Cadeia obrigatória:

```text
VEREDITO
   ↓
EVIDÊNCIA
   ↓
DOCUMENTO
   ↓
VERSÃO
   ↓
PÁGINA / SEÇÃO / TRECHO
```

Quando um nível de metadado não estiver disponível, o sistema deve omiti-lo ou usar uma descrição conservadora. Nunca inventar página, seção, documento ou conteúdo.

## 44.2 Regra de seleção do estado atual

Para entidades versionadas, **não usar a ordem incidental de um relacionamento ORM para determinar o registro mais recente**.

Exemplo incorreto:

```python
latest = prop.verdicts[-1] if prop.verdicts else None
```

Exemplo canônico para Veredito:

```python
latest = db.scalar(
    select(models.Verdict)
    .where(models.Verdict.property_id == property_id)
    .order_by(
        models.Verdict.analysis_version.desc(),
        models.Verdict.id.desc()
    )
)
```

A mesma regra deve ser aplicada somente quando houver risco funcional equivalente em outras entidades versionadas: a seleção do estado atual precisa ser determinística.

## 44.3 Validação manual do imóvel de referência

A validação pela UI do imóvel `633` confirmou:

- histórico com Análise V8;
- Checklist com 7 itens CONFIRMADO e 20 PENDENTE;
- documentos com versionamento visível;
- Veredito ainda exibindo V7;
- evidências exibidas como IDs internos.

Essas duas inconsistências são requisitos explícitos de correção antes da validação operacional V8 → V9.

## 44.4 Task 70 — escopo fechado

A Task 70 corrige somente:

1. seleção determinística do Veredito mais recente;
2. teste de regressão dessa seleção;
3. apresentação amigável das evidências na tela de Veredito;
4. contrato de dados necessário para o frontend renderizar documento/categoria/versão/página/seção/trecho quando esses dados existirem;
5. testes de regressão da apresentação/contrato.

Fora do escopo:

- nova regra de negócio;
- alteração do Verdict Engine;
- alteração do Risk Engine;
- alteração do RAG;
- alteração dos agentes;
- alteração do Checklist;
- migration;
- nova análise real;
- geração da V9;
- refatoração geral do backend/frontend.

## 44.5 Critério de validação visual

Após a Task 70, o usuário deve conseguir abrir o imóvel 633 e entender o Veredito sem conhecer o banco de dados.

Resultado esperado:

```text
Veredito
  → Análise V8

Evidências vinculadas
  → documento legível
  → categoria/tipo
  → versão, quando disponível
  → página/seção, quando disponível
  → trecho/descrição, quando disponível
```

Os IDs internos podem continuar existindo tecnicamente, mas não devem ser a informação principal apresentada ao usuário.

## 44.6 Sequência de validação

```text
TASK 70
   ↓
pytest
   ↓
auditoria do commit
   ↓
rebuild / health
   ↓
UI do imóvel 633
   ↓
Veredito = V8
   ↓
evidências legíveis
   ↓
retomar V8 → V9
```

A validação incremental só será considerada concluída após a execução controlada desse fluxo.


---

# 45. TASK 70 — Regra consolidada de estado atual e evidências na UI

A Task 70 consolidou duas regras funcionais para a camada de apresentação.

## 45.1 Estado atual de entidades versionadas

Quando uma entidade possui versões, a API não deve determinar o estado atual pela posição incidental de uma coleção ORM.

Regra:

```text
ESTADO ATUAL
    ↓
maior versão semântica
    ↓
desempate determinístico por ID
```

Para Veredito:

```python
select(models.Verdict)
    .where(models.Verdict.property_id == property_id)
    .order_by(
        models.Verdict.analysis_version.desc(),
        models.Verdict.id.desc()
    )
```

## 45.2 Evidências para o usuário final

A rastreabilidade interna continua baseada em `evidence_id`, porém a UI deve priorizar uma representação compreensível:

```text
EVIDENCE ID
    ↓
Evidence
    ↓
DocumentVersion
    ↓
Document
    ↓
página / seção / fato / trecho
```

Metadados ausentes não devem ser inventados.

## 45.3 Validação da Task 70

Commit:

```text
7f8f62454288b96723ea15909c0c967dfbcae3d2
```

Resultados:

```text
Backend: 267 passed
Frontend: 90 Vitest passed
TypeScript: tsc --noEmit OK
```

A V8 do imóvel 633 permanece intacta e nenhuma V9 foi gerada.

## 45.4 Próxima sequência

```text
TASK 70 aprovada
       ↓
rebuild / health
       ↓
UI do imóvel 633
       ↓
confirmar Veredito V8
       ↓
confirmar evidências legíveis
       ↓
criar/selecionar DomainEvent de teste
       ↓
POST /api/imoveis/633/eventos/{event_id}/reanalisar
       ↓
ImpactAnalyzer
       ↓
reanálise incremental
       ↓
V9
       ↓
auditoria do resultado
```

A execução da V9 continua separada da Task 70 e deve ocorrer somente após a confirmação visual.


# 46. ADDENDUM — Seleção determinística da execução do Checklist no Veredito

Durante a validação real da UI do imóvel 633, foi confirmado que o Checklist V8 possui 27 resultados, sendo 7 CONFIRMADO e 20 PENDENTE. O Veredito V8 persistido possui 28 pending_items: 27 perguntas do Checklist mais uma pendência financeira sobre a fórmula canônica de preço máximo.

A causa é a função latest_execution():

    def latest_execution(prop: models.Property):
        return next(iter(reversed(prop.checklist_executions)), None)

Relacionamentos ORM não devem definir o estado atual pela posição incidental da coleção. Para ChecklistExecution, a regra passa a ser:

    return db.scalar(
        select(models.ChecklistExecution)
        .where(models.ChecklistExecution.property_id == prop.id)
        .order_by(
            models.ChecklistExecution.analysis_version.desc(),
            models.ChecklistExecution.id.desc(),
        )
    )

A correção deve ser mínima e não deve alterar as regras do Checklist ou do Verdict Engine. O motor deve continuar consolidando pendências do Checklist e pendências financeiras legítimas.

## 46.1 Task 71 — escopo

1. Corrigir latest_execution() de forma determinística.
2. Adicionar teste com múltiplas execuções fora de ordem.
3. Garantir alinhamento entre a versão da Analysis e a execução do Checklist usada pelo Veredito.
4. Preservar a pendência financeira existente.
5. Executar suíte completa.
6. Não alterar Verdict Engine, Risk Engine, RAG, LangGraph, agentes, Checklist Mestre, modelos ou migrations.
7. Não executar nova análise real e não gerar V9.

**Commit esperado:** fix: corrige selecao da execucao do checklist

## 46.2 Critério de aceite

    Checklist V8
    7 CONFIRMADO
    20 PENDENTE

            ↓

    Veredito V8
    20 pendências do Checklist
    + pendências financeiras legítimas, se existentes

Os sete itens confirmados na V8 não podem reaparecer como pendentes no Veredito da mesma análise.

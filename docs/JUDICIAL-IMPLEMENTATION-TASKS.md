# Judicial API — Implementation Tasks

**Documento:** JUDICIAL-IMPLEMENTATION-TASKS.md  
**Versão:** 1.0  
**Base:** `docs/JUDICIAL-API-SPEC.md`  
**Objetivo:** dividir a implementação em tarefas pequenas e controladas para execução sequencial pelo Kiro.

---

# 1. Objetivo da implementação

Implementar um **módulo Judicial API independente**, preparado para ser posteriormente consumido pelo Radar Leilão.

A Judicial API será responsável por:

- consultar fontes judiciais públicas disponíveis no ecossistema DataJud/CNJ;
- consultar múltiplos tribunais/fontes em paralelo;
- normalizar respostas em um contrato único;
- registrar fontes consultadas e falhas;
- diferenciar ausência de resultados de consulta incompleta;
- permitir reprocessamento;
- manter histórico e auditoria;
- gerar evidências/sinais processuais;
- esconder do consumidor os detalhes específicos de cada tribunal/provider.

## Regra arquitetural principal

O consumidor deverá utilizar **uma única API REST**, independentemente de quantos tribunais ou ramos da Justiça forem consultados.

Exemplo:

```
POST /api/v1/judicial/search
```

A aplicação não deverá precisar chamar diretamente:

- TJPR;
- TJSP;
- TRF;
- TRT;
- TRE;
- STJ;
- TST;
- TSE;
- STM;
- ou qualquer outro provider/tribunal.

A Judicial API fará a orquestração internamente.

---

# 2. Cobertura judicial desejada

## 2.1 Justiça Estadual

**Somente:**

- TJPR — Paraná
- TJSP — São Paulo

Não implementar consulta aos demais Tribunais de Justiça estaduais neste ciclo.

A arquitetura deve continuar configurável para permitir futura expansão, mas **não implementar os demais estados agora**.

---

## 2.2 Justiça Federal

Consultar todos os TRFs disponibilizados pelo DataJud/CNJ e aplicáveis à pesquisa:

- TRF1
- TRF2
- TRF3
- TRF4
- TRF5
- TRF6

---

## 2.3 Justiça do Trabalho

Consultar os TRTs disponibilizados pelo DataJud/CNJ:

- TRT1
- TRT2
- TRT3
- TRT4
- TRT5
- TRT6
- TRT7
- TRT8
- TRT9
- TRT10
- TRT11
- TRT12
- TRT13
- TRT14
- TRT15
- TRT16
- TRT17
- TRT18
- TRT19
- TRT20
- TRT21
- TRT22
- TRT23
- TRT24

O catálogo efetivo deve ser validado na documentação oficial vigente antes do cadastro.

---

## 2.4 Tribunais Superiores

Consultar, quando disponibilizados e suportados pela fonte:

- STJ
- TST
- TSE
- STM

---

## 2.5 Justiça Eleitoral

Consultar as fontes eleitorais disponibilizadas pelo DataJud/CNJ:

- TSE
- TREs

A lista efetiva de endpoints/aliases deverá ser validada no catálogo oficial vigente.

---

## 2.6 Justiça Militar

Consultar os tribunais militares disponibilizados pela fonte, quando disponíveis e suportados:

- STM
- TJMMG
- TJMRS
- TJMSP

Não assumir que todos estarão disponíveis. O catálogo oficial deve ser a fonte de verdade.

---

# 3. Regra de seleção de fontes

A API deve permitir:

### Pesquisa ampla

```json
{
  "cpf": "12345678900",
  "execution_mode": "PARALLEL"
}
```

Nesse caso, o orchestrator seleciona todas as fontes habilitadas e aplicáveis ao escopo configurado.

### Pesquisa restrita

```json
{
  "cpf": "12345678900",
  "tribunals": ["TJPR", "TJSP", "TRF4"]
}
```

### Pesquisa por ramo

```json
{
  "cpf": "12345678900",
  "justice_types": ["FEDERAL", "LABOR"]
}
```

A seleção deve respeitar capabilities de cada fonte.

**Nunca assumir que todos os tribunais suportam todos os critérios.**

---

# 4. Uma única API REST

O contrato externo deve ser unificado.

Principais endpoints:

```
GET  /health

POST /api/v1/judicial/search

GET  /api/v1/judicial/search/{search_id}

GET  /api/v1/judicial/search/{search_id}/sources

POST /api/v1/judicial/search/{search_id}/retry

GET  /api/v1/judicial/tribunals

GET  /api/v1/judicial/capabilities

GET  /api/v1/judicial/providers/status
```

O consumidor não deve conhecer URLs individuais do DataJud nem endpoints específicos dos tribunais.

---

# 5. Regra de escopo para o Kiro

## MUITO IMPORTANTE

As tarefas abaixo devem ser executadas **uma por vez**.

Fluxo obrigatório:

```
JUR-01
  ↓
commit
  ↓
validação
  ↓
JUR-02
  ↓
commit
  ↓
validação
  ↓
...
```

Ao executar uma task:

> **Implementar somente a task solicitada. Não antecipar implementação de tasks futuras, mesmo que os requisitos estejam descritos em JUDICIAL-API-SPEC.md.**

A SPEC é a fonte completa de requisitos.

Este documento é a ordem de execução.

---

# 6. JUR-01 — Fundação

## Objetivo

Criar a fundação técnica do módulo Judicial API sem implementar ainda a integração real com o DataJud.

## Implementar

- estrutura do módulo;
- configuração base;
- aplicação REST;
- health check;
- contrato inicial de erro;
- correlation ID;
- logging estruturado básico;
- interfaces/base para Provider;
- interfaces/base para Registry;
- modelos/DTOs principais;
- enumerações de justice type/status;
- configuração externa;
- estrutura inicial de testes;
- documentação mínima de execução local.

## Preparar

Interface conceitual:

```
JudicialProvider
  ├── search()
  ├── get_capabilities()
  ├── health_check()
  └── normalize()
```

## Não implementar nesta task

- chamada real ao DataJud;
- consulta a tribunais;
- cadastro completo dos tribunais;
- PostgreSQL completo;
- sinais jurídicos;
- retry;
- paginação;
- concorrência de consultas;
- reanálise;
- integração com Radar;
- LLM;
- RAG;
- MCP.

## Critérios de aceite

- aplicação sobe localmente;
- `GET /health` funciona;
- estrutura de módulos está organizada;
- contrato de erro existe;
- correlation ID funciona;
- testes básicos passam;
- não existe segredo hardcoded;
- nenhuma chamada real ao DataJud é necessária para os testes.

## Commit esperado

```
feat(judicial): create judicial api foundation
```

---

# 7. JUR-02 — DataJud Provider e catálogo

## Objetivo

Implementar a abstração concreta do DataJud e o catálogo configurável das fontes desejadas.

## Implementar

- DataJudProvider;
- configuração de endpoints;
- capabilities;
- Tribunal Registry;
- Provider Registry;
- cadastro das fontes do escopo;
- construção das queries;
- autenticação conforme documentação oficial;
- encapsulamento da API específica do DataJud;
- paginação específica do provider;
- normalização inicial de processos.

## Cobertura obrigatória

### Estadual

```
TJPR
TJSP
```

### Federal

```
TRF1
TRF2
TRF3
TRF4
TRF5
TRF6
```

### Trabalhista

```
TRT1 ... TRT24
```

### Superiores

```
STJ
TST
TSE
STM
```

### Eleitoral

```
TSE
TREs disponíveis no catálogo oficial
```

### Militar

```
STM
TJMMG
TJMRS
TJMSP
```

## Regra importante

Não cadastrar nem implementar os demais TJs estaduais neste ciclo.

A arquitetura deve permitir adicioná-los futuramente sem alteração do contrato REST.

## Validação obrigatória

Antes de implementar cada capability específica:

- validar documentação oficial;
- validar endpoint;
- validar alias;
- validar autenticação;
- validar campo pesquisável;
- validar paginação;
- validar limites.

Se não houver comprovação:

```
PENDING_VALIDATION
```

ou:

```
UNSUPPORTED_SEARCH_CRITERIA
```

## Não implementar nesta task

- análise jurídica final;
- correlação com matrícula;
- Risk Engine;
- Verdict;
- integração com Radar.

## Critérios de aceite

- DataJudProvider isolado;
- endpoints configuráveis;
- capabilities configuráveis;
- fontes do escopo cadastradas;
- consulta individual a uma fonte funciona;
- contrato externo permanece unificado;
- demais estados não são consultados.

## Commit esperado

```
feat(judicial): add datajud provider and court registry
```

---

# 8. JUR-03 — Orquestração, persistência e resiliência

## Objetivo

Transformar a consulta individual em uma pesquisa multi-fonte robusta.

## Implementar

- Search Orchestrator;
- execução paralela;
- controle de concorrência;
- timeout por fonte;
- timeout global;
- retry;
- exponential backoff + jitter;
- rate limit;
- limites de paginação;
- status COMPLETED;
- status EMPTY;
- status PARTIAL;
- status FAILED;
- persistência;
- histórico;
- deduplicação;
- registro por fonte;
- erros normalizados;
- eventos;
- idempotência;
- reanálise de fontes que falharam.

## Regra crítica

Se:

```
TJPR = SUCCESS
TJSP = SUCCESS
TRF4 = TIMEOUT
TRT9 = SUCCESS
```

o resultado não pode ser `EMPTY`.

Deve ser:

```
PARTIAL
```

## Critérios de aceite

- consulta ampla executa fontes em paralelo;
- uma fonte com erro não derruba as demais;
- fontes falhas ficam identificadas;
- resultado parcial é transparente;
- retry funciona;
- reanálise consulta somente fontes necessárias;
- processos duplicados são eliminados;
- pesquisa fica auditável;
- testes unitários e integração passam.

## Commit esperado

```
feat(judicial): add orchestration persistence and resilience
```

---

# 9. JUR-04 — Sinais e análise processual

## Objetivo

Transformar processos normalizados em evidências/sinais jurídicos estruturados.

## Implementar

- Signal Engine;
- regras versionadas;
- sinais;
- severidade;
- confidence;
- evidência;
- homônimos;
- distinção entre processo e imóvel;
- categorização processual;
- persistência dos sinais.

## Exemplos de sinais

```
PENHORA
ARRESTO
INDISPONIBILIDADE
EXECUCAO
EXECUCAO_FISCAL
COBRANCA
FALENCIA
RECUPERACAO_JUDICIAL
INSOLVENCIA
EMBARGOS_A_EXECUCAO
EMBARGOS_DE_TERCEIRO
ALIENACAO_FIDUCIARIA
HIPOTECA
USUCAPIAO
DESAPROPRIACAO
INVENTARIO
PARTILHA
ACAO_TRABALHISTA
```

## Regra jurídica fundamental

Não transformar automaticamente:

```
movimentação contendo "penhora"
```

em:

```
imóvel está penhorado
```

O resultado deve representar evidência:

```
PROPERTY_PENHORA_EVIDENCE
```

A correlação definitiva com o imóvel será responsabilidade do módulo jurídico do Radar.

## Não implementar nesta task

- decisão jurídica definitiva;
- parecer jurídico;
- Risk Engine;
- Verdict;
- preço máximo;
- integração final com matrícula do Radar.

## Critérios de aceite

- sinais são detectados;
- regras são versionadas;
- evidência é armazenada;
- homônimos são tratados;
- processo não é confundido automaticamente com imóvel;
- testes passam.

## Commit esperado

```
feat(judicial): add legal signal engine
```

---

# 10. JUR-05 — REST completa, documentação e E2E

## Objetivo

Finalizar a Judicial API como módulo consumível externamente.

## Implementar

- endpoints REST definidos na SPEC;
- OpenAPI/Swagger;
- autenticação da API;
- autorização;
- rate limiting;
- métricas;
- observabilidade;
- auditoria;
- documentação;
- testes E2E;
- smoke tests;
- testes reais opcionais;
- hardening básico;
- revisão final de segurança;
- revisão de compliance.

## Testes E2E

Devem validar:

```
request
 ↓
REST
 ↓
orchestrator
 ↓
DataJudProvider/mock
 ↓
normalização
 ↓
persistência
 ↓
signals
 ↓
response
```

## Testes reais

Não devem fazer parte da suíte padrão.

Exemplo:

```bash
RUN_REAL_DATAJUD_TESTS=true pytest tests/real
```

## Critérios de aceite

- contrato REST estável;
- OpenAPI disponível;
- pesquisa multi-fonte funciona;
- resultado normalizado;
- fontes individuais são rastreáveis;
- retry funciona;
- sinais aparecem;
- auditoria funciona;
- testes passam;
- aplicação está pronta para ser consumida pelo Radar.

## Commit esperado

```
feat(judicial): complete judicial api
```

---

# 11. Integração futura com o Radar Leilão

A Judicial API é um **módulo independente**.

Ela não deve incorporar o Risk Engine do Radar.

Arquitetura futura:

```
                         RADAR LEILÃO
                              │
               ┌──────────────┼──────────────┐
               │              │              │
               ▼              ▼              ▼
           Jurídico       Financeiro       Mercado
               │
               ▼
         Judicial API
               │
       ┌───────┼────────┐
       ▼       ▼        ▼
    TJPR/TJSP Federal  Outros
       │       │        │
       └───────┼────────┘
               ▼
        Processos/Evidências
               │
               ▼
       Correlação com imóvel
               │
               ▼
          Risco Jurídico
               │
               └──────────────┐
                              ▼
                         Risk Engine
                              │
                     ┌────────┴────────┐
                     ▼                 ▼
                 Checklist          Verdict
                                         │
                                         ▼
                                   Preço Máximo
```

## Regra

A Judicial API responde:

> Quais processos/evidências foram encontrados?

O módulo Jurídico do Radar responde:

> Qual a relação dessas evidências com o imóvel analisado e qual o impacto jurídico?

O Radar responde:

> Como o risco jurídico, financeiro, de mercado e de ocupação afeta a análise final do imóvel?

---

# 12. Regras para economia de créditos do Kiro

1. Executar somente uma task por vez.
2. Não implementar task futura.
3. Não refatorar módulos não relacionados.
4. Não criar infraestrutura AWS.
5. Não criar frontend nesta etapa.
6. Não integrar LLM/RAG/MCP.
7. Não implementar todos os estados brasileiros.
8. Não criar funcionalidades não descritas na task atual.
9. Priorizar testes automatizados.
10. Ao finalizar a task, parar e aguardar nova instrução.

## Regra de parada

Ao cumprir os critérios de aceite da task atual:

> **PARAR. Não iniciar automaticamente a próxima task.**

---

# 13. Ordem oficial

```
JUR-01 Fundação
      ↓
JUR-02 DataJud + Registry
      ↓
JUR-03 Orquestração + Persistência + Resiliência
      ↓
JUR-04 Sinais Jurídicos
      ↓
JUR-05 REST + E2E + Hardening
```

---

# 14. Fonte de verdade

A ordem de prioridade é:

1. documentação oficial vigente do CNJ/DataJud;
2. `docs/JUDICIAL-API-SPEC.md`;
3. `docs/JUDICIAL-IMPLEMENTATION-TASKS.md`;
4. task específica enviada ao Kiro.

Quando houver conflito, a documentação oficial deve prevalecer para capacidades e limitações externas.

---

# 15. Resultado esperado

Ao final das cinco tasks deverá existir uma Judicial API independente capaz de:

- receber uma única requisição REST;
- consultar múltiplas fontes judiciais;
- consultar TJPR e TJSP no ramo estadual;
- consultar os TRFs;
- consultar os TRTs;
- consultar tribunais superiores;
- consultar fontes eleitorais;
- consultar fontes militares disponíveis;
- executar consultas em paralelo;
- normalizar resultados;
- registrar fontes e falhas;
- diferenciar EMPTY de PARTIAL;
- reprocessar fontes;
- persistir histórico;
- detectar sinais processuais;
- expor contrato REST unificado;
- estar pronta para ser integrada ao módulo Jurídico do Radar Leilão.

**Fora do escopo atual:** consulta aos demais TJs estaduais, integração final com Risk Engine/Verdict do Radar, frontend, LLM/RAG e MCP.

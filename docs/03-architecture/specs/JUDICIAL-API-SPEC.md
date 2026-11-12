# Judicial API — Especificação Técnica Completa

**Versão:** 1.0  
**Status:** Especificação técnica  
**Escopo:** Módulo independente para pesquisa processual judicial nacional  
**Idioma:** Português

---

## 1. Objetivo

Este documento especifica uma API independente para pesquisa processual judicial nacional, inicialmente utilizando as APIs públicas do DataJud/CNJ.

O módulo deverá:

- consultar tribunais de diferentes ramos da Justiça;
- consultar múltiplos tribunais em paralelo;
- normalizar respostas diferentes em um único contrato;
- identificar processos relacionados às pessoas pesquisadas;
- identificar sinais jurídicos relevantes;
- registrar quais fontes foram consultadas;
- registrar quais fontes falharam;
- diferenciar ausência de resultados de consulta incompleta;
- permitir reprocessamento posterior;
- manter histórico e auditoria;
- proteger credenciais;
- possuir arquitetura preparada para futuros provedores;
- oferecer uma API simples, estável e independente dos detalhes de cada tribunal.

### Princípio central

O consumidor da API não deve precisar conhecer detalhes específicos do DataJud, Elasticsearch, URLs, aliases ou formatos internos de cada tribunal.

A arquitetura deve separar:

```text
Consumidor
    ↓
Judicial API
    ↓
Orquestração / Normalização
    ↓
Provider
    ↓
Tribunal / Fonte judicial
```

---

# 2. Fonte inicial

O primeiro provider será o **DataJud / CNJ**.

Documentação oficial:

- https://datajud-wiki.cnj.jus.br/api-publica/
- https://datajud-wiki.cnj.jus.br/api-publica/acesso/
- https://datajud-wiki.cnj.jus.br/api-publica/endpoints/
- https://datajud-wiki.cnj.jus.br/api-publica/exemplos/
- https://datajud-wiki.cnj.jus.br/api-publica/glossario/

Antes da implementação, toda a documentação oficial deverá ser revisada novamente.

---

# 3. Regra fundamental: não assumir capacidades

A implementação não deve assumir que um tribunal suporta determinado critério de pesquisa.

Exemplos:

- nome;
- CPF;
- CNPJ;
- número do processo;
- assunto;
- classe;
- órgão julgador.

As capacidades deverão ser validadas pela documentação oficial e/ou por validação técnica.

Quando um critério não for suportado:

```json
{
  "code": "UNSUPPORTED_SEARCH_CRITERIA",
  "message": "O critério solicitado não é suportado por esta fonte.",
  "retryable": false
}
```

Nunca simular uma capacidade inexistente.

---

# 4. Cobertura nacional

O catálogo de tribunais deverá ser baseado no catálogo oficial atual do DataJud.

A arquitetura deve contemplar, conforme disponibilidade oficial:

## Tribunais Superiores

- TST
- TSE
- STJ
- STM

## Justiça Federal

- TRF1
- TRF2
- TRF3
- TRF4
- TRF5
- TRF6

## Justiça Estadual

- TJAC
- TJAL
- TJAM
- TJAP
- TJBA
- TJCE
- TJDFT
- TJES
- TJGO
- TJMA
- TJMG
- TJMS
- TJMT
- TJPA
- TJPB
- TJPE
- TJPI
- TJPR
- TJRJ
- TJRN
- TJRO
- TJRR
- TJRS
- TJSC
- TJSE
- TJSP
- TJTO

## Justiça do Trabalho

- TRT1 até TRT24

## Justiça Eleitoral

- TSE
- TREs

## Justiça Militar Estadual

Quando disponíveis no catálogo:

- TJMMG
- TJMRS
- TJMSP

> A lista acima é referência inicial. Antes da implementação, deve ser comparada com o catálogo oficial vigente.

---

# 5. Arquitetura

```text
                         ┌──────────────────────┐
                         │      Consumidor      │
                         └──────────┬───────────┘
                                    │
                              HTTP / JSON
                                    │
                                    ▼
                    ┌────────────────────────────┐
                    │        Judicial API        │
                    │                            │
                    │ Search Orchestrator        │
                    │ Tribunal Registry          │
                    │ Provider Registry          │
                    │ Normalization              │
                    │ Legal Signal Engine        │
                    │ Persistence                │
                    │ Audit                      │
                    │ Observability              │
                    └──────────────┬─────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    │                             │
                    ▼                             ▼
             ┌───────────────┐             ┌───────────────┐
             │ DataJudProvider│             │ Futuro Provider│
             └───────┬───────┘             └───────────────┘
                     │
       ┌─────────────┼──────────────────────┐
       │             │                      │
       ▼             ▼                      ▼
     TJPR          TJSP                   TRF4
       │             │                      │
       ▼             ▼                      ▼
     TRT9          STJ                    TRF3
       │             │                      │
       └─────────────┼──────────────────────┘
                     ▼
               Normalização
                     │
                     ▼
             Processos encontrados
                     │
              ┌──────┴───────┐
              ▼              ▼
        Sinais jurídicos   Erros
              │              │
              └──────┬───────┘
                     ▼
                Resultado
                     │
                     ▼
                 Reanálise
```

---

# 6. Componentes

## 6.1 Search Orchestrator

Responsável por:

1. validar a requisição;
2. identificar fontes aplicáveis;
3. verificar capacidades;
4. criar a pesquisa;
5. disparar consultas;
6. controlar concorrência;
7. aplicar timeout;
8. aplicar retry;
9. coletar respostas;
10. normalizar;
11. deduplicar;
12. gerar sinais;
13. persistir;
14. calcular status;
15. determinar necessidade de reanálise.

---

## 6.2 Tribunal Registry

Responsável pelo cadastro de:

- tribunais;
- aliases;
- UF;
- ramo da Justiça;
- provider;
- endpoints;
- capacidades;
- status;
- prioridades.

---

## 6.3 Provider Registry

Responsável por identificar:

- provider;
- tribunal;
- endpoint;
- configuração;
- credencial;
- capacidades.

---

## 6.4 Normalization Layer

Transforma respostas específicas de cada fonte em um contrato único.

Exemplo:

```text
Resposta TJPR ─┐
Resposta TJSP ─┼──→ Normalização ─→ Processo Normalizado
Resposta TRF4 ─┤
Resposta TRT9 ─┘
```

---

## 6.5 Legal Signal Engine

Identifica evidências processuais relevantes.

O mecanismo não deve emitir parecer jurídico. Sua função é detectar sinais e evidências.

---

## 6.6 Persistence

Armazena:

- pesquisas;
- fontes;
- processos;
- partes;
- assuntos;
- movimentos;
- sinais;
- erros;
- eventos;
- configurações.

---

# 7. Contrato principal

Endpoint:

```http
POST /api/v1/judicial/search
```

Exemplo:

```json
{
  "name": "Nome da Pessoa",
  "cpf": "00000000000",
  "cnpj": null,
  "process_number": null,
  "uf": "PR",
  "city": null,
  "tribunals": [],
  "justice_types": [],
  "include_movements": true,
  "include_parties": true,
  "include_subjects": true,
  "page_size": 100,
  "max_pages_per_source": 10,
  "execution_mode": "PARALLEL"
}
```

---

# 8. Critérios de pesquisa

O contrato deve permitir, quando suportados:

### Pessoa

```text
name
cpf
cnpj
```

### Processo

```text
process_number
```

### Localização

```text
uf
city
```

### Tribunal

```text
tribunals[]
```

### Justiça

```text
justice_types[]
```

### Classificação

```text
class
subject
court
```

### Conteúdo

```text
include_movements
include_parties
include_subjects
```

O provider deverá informar suas capabilities.

---

# 9. Exemplo: pesquisa por CPF

```http
POST /api/v1/judicial/search
Content-Type: application/json
```

```json
{
  "cpf": "12345678900",
  "uf": "PR",
  "include_movements": true,
  "include_parties": true,
  "include_subjects": true
}
```

---

# 10. Exemplo: pesquisa por processo

```json
{
  "process_number": "0000000-00.0000.0.00.0000",
  "include_movements": true
}
```

---

# 11. Exemplo: pesquisa restrita a tribunais

```json
{
  "cpf": "12345678900",
  "tribunals": [
    "TJPR",
    "TJSC",
    "TJSP"
  ],
  "include_movements": true
}
```

---

# 12. Exemplo: pesquisa nacional

```json
{
  "cpf": "12345678900",
  "execution_mode": "PARALLEL",
  "include_movements": true
}
```

O orchestrator selecionará as fontes aplicáveis e fará as consultas respeitando os limites de concorrência.

---

# 13. Execução paralela

Consultas independentes devem ser executadas em paralelo, porém com concorrência limitada.

Configurações:

```text
max_global_concurrency
max_provider_concurrency
max_tribunal_concurrency
```

Valores iniciais sugeridos:

```text
global = 20
provider = 20
tribunal = 1
```

Esses valores devem ser configuráveis.

---

# 14. Timeout

Cada fonte deverá possuir timeout próprio.

Exemplo:

```text
TJPR → 8 segundos
TJSP → 8 segundos
TRF4 → 10 segundos
```

Também deve existir timeout global.

Exemplo:

```text
global_timeout = 60 segundos
```

---

# 15. Falha isolada

A falha de um tribunal não pode cancelar a pesquisa inteira.

Exemplo:

```text
TJPR → SUCCESS
TJSC → SUCCESS
TJSP → TIMEOUT
TRF4 → SUCCESS
TRF3 → ERROR
```

Resultado:

```text
PARTIAL
```

e não:

```text
FAILED
```

---

# 16. Status da pesquisa

## COMPLETED

Todas as fontes aplicáveis responderam corretamente.

## EMPTY

Todas as fontes aplicáveis responderam corretamente e nenhum processo foi encontrado.

## PARTIAL

Uma ou mais fontes:

- falharam;
- deram timeout;
- ficaram indisponíveis;
- não suportaram o critério;
- tiveram resultado limitado.

## FAILED

Não foi possível obter um resultado confiável da pesquisa.

### Regra crítica

`EMPTY` é diferente de `PARTIAL`.

---

# 17. Exemplo de resultado

```json
{
  "search_id": "7c7d2d4a-2f3d-4f6a-9f1d-123456789abc",
  "status": "PARTIAL",
  "completeness": {
    "requested_sources": 100,
    "successful_sources": 96,
    "failed_sources": 4,
    "unsupported_sources": 0
  },
  "sources": [],
  "processes": [],
  "signals": [],
  "warnings": [],
  "reanalyze": {
    "recommended": true,
    "reason": "TRIBUNAL_UNAVAILABLE",
    "sources_affected": [
      "TJSP",
      "TRF3"
    ]
  }
}
```

---

# 18. Resultado por fonte

Cada tribunal deve possuir seu próprio resultado.

```json
{
  "provider": "DATAJUD",
  "tribunal": "TJPR",
  "justice_type": "STATE",
  "status": "SUCCESS",
  "http_status": 200,
  "duration_ms": 812,
  "pages": 2,
  "result_count": 7,
  "error": null
}
```

---

# 19. Resultado incompleto

```json
{
  "provider": "DATAJUD",
  "tribunal": "TJSP",
  "justice_type": "STATE",
  "status": "TIMEOUT",
  "http_status": null,
  "duration_ms": 8000,
  "pages": 0,
  "result_count": 0,
  "error": {
    "code": "PROVIDER_TIMEOUT",
    "retryable": true
  }
}
```

---

# 20. Reanálise

Se um tribunal não respondeu, isso não significa ausência de processos.

Exemplo:

```text
TJPR → SUCCESS
TJSP → TIMEOUT
TRF4 → SUCCESS
```

Não deve resultar em:

> Não existem processos.

Deve resultar em:

> A pesquisa foi concluída parcialmente. O TJSP não respondeu e precisa ser consultado novamente.

---

# 21. Endpoint de reanálise

```http
POST /api/v1/judicial/search/{search_id}/retry
```

Por padrão, devem ser reprocessadas somente as fontes que falharam.

Fontes já concluídas não precisam ser consultadas novamente, salvo solicitação explícita.

---

# 22. Erros normalizados

O consumidor nunca deve depender dos códigos internos do DataJud.

Catálogo:

```text
AUTHENTICATION_ERROR
AUTHORIZATION_ERROR
RATE_LIMITED
BAD_REQUEST
NOT_FOUND
PROVIDER_TIMEOUT
PROVIDER_UNAVAILABLE
PROVIDER_SERVER_ERROR
INVALID_RESPONSE
PARSE_ERROR
UNSUPPORTED_SEARCH_CRITERIA
CONFIGURATION_ERROR
UNKNOWN_ERROR
RESULT_LIMIT_REACHED
```

---

# 23. Estrutura de erro

```json
{
  "code": "PROVIDER_TIMEOUT",
  "message": "O tribunal não respondeu dentro do tempo limite.",
  "retryable": true,
  "provider": "DATAJUD",
  "tribunal": "TJSP",
  "timestamp": "2026-09-26T10:00:00Z",
  "correlation_id": "uuid"
}
```

Nunca retornar:

- stack trace;
- API key;
- senha;
- informações internas desnecessárias.

---

# 24. Retry

Retry automático somente para erros transitórios.

### Retry

```text
TIMEOUT
429 / RATE_LIMITED
5xx
PROVIDER_UNAVAILABLE
```

### Não retry automático

```text
401
403
400
UNSUPPORTED_SEARCH_CRITERIA
CONFIGURATION_ERROR
```

---

# 25. Backoff

Utilizar exponential backoff com jitter.

Exemplo:

```text
tentativa 1 → 500 ms
tentativa 2 → 1 s
tentativa 3 → 2 s
```

Os parâmetros devem ser configuráveis.

---

# 26. Paginação

A paginação específica do DataJud deve ficar totalmente encapsulada dentro do `DataJudProvider`.

O domínio não deve conhecer detalhes do Elasticsearch ou `search_after`.

```text
Judicial API
      ↓
DataJudProvider
      ↓
Página 1
      ↓
Página 2
      ↓
Página 3
      ↓
...
      ↓
Processos normalizados
```

---

# 27. Limites

Configurações:

```text
page_size
max_pages
max_results
global_timeout
```

Se o limite for atingido:

```text
RESULT_LIMIT_REACHED
```

A pesquisa não deve ser apresentada como completamente exaustiva.

Mensagem:

> A consulta atingiu o limite configurado e pode haver resultados adicionais.

---

# 28. Modelo normalizado

Independentemente da origem:

```json
{
  "process_number": "0000000-00.0000.0.00.0000",
  "tribunal": "TJPR",
  "justice_type": "STATE",
  "jurisdiction": "1º Grau",
  "court": "Vara",
  "class": {},
  "subjects": [],
  "parties": [],
  "movements": [],
  "priority": [],
  "electronic": true,
  "system": {},
  "last_movement_at": "2026-09-01",
  "source": {}
}
```

---

# 29. Processo

Campos mínimos:

```text
process_number
tribunal
justice_type
jurisdiction
court
class
subjects
parties
movements
priority
electronic
system
last_movement_at
source
```

---

# 30. Partes

Exemplo:

```json
{
  "name": "JOÃO DA SILVA",
  "document": "00000000000",
  "document_type": "CPF",
  "role": "DEFENDANT",
  "party_type": "PERSON"
}
```

A ausência de CPF/CNPJ não deve ser tratada automaticamente como erro.

---

# 31. Homônimos

Encontrar uma pessoa com o mesmo nome não significa confirmar identidade.

Exemplo:

```text
JOÃO DA SILVA
```

deve ser tratado com cautela quando não houver CPF/CNPJ ou outra evidência suficiente.

Possível sinal:

```text
HOMONYM_POSSIBLE
```

Mensagem:

> Foi localizado processo com nome semelhante, mas não há evidência suficiente para confirmar que pertence à pessoa pesquisada.

---

# 32. Movimentações

Exemplo:

```json
{
  "movement_date": "2026-09-01",
  "code": "123",
  "description": "Descrição da movimentação"
}
```

As movimentações devem ser armazenadas separadamente e, quando possível, vinculadas ao identificador original da fonte.

---

# 33. Deduplicação

Um mesmo processo não deve aparecer repetidamente.

Chave lógica sugerida:

```text
provider
+
tribunal
+
process_number
```

Movimentações podem utilizar:

```text
source_identifier
```

ou hash determinístico.

---

# 34. Sinais jurídicos

O sistema poderá detectar sinais como:

```text
PENHORA
ARRESTO
INDISPONIBILIDADE
EXECUÇÃO
EXECUÇÃO_FISCAL
CUMPRIMENTO_DE_SENTENÇA
COBRANÇA
FALÊNCIA
RECUPERAÇÃO_JUDICIAL
INSOLVÊNCIA
EMBARGOS_À_EXECUÇÃO
EMBARGOS_DE_TERCEIRO
ALIENAÇÃO_FIDUCIÁRIA
HIPOTECA
USUCAPIÃO
DESAPROPRIAÇÃO
INVENTÁRIO
PARTILHA
AÇÃO_TRABALHISTA
```

Esses sinais representam evidências encontradas em dados processuais.

---

# 35. Regra importante para penhora

Evitar:

```json
{
  "property_seized": true
}
```

quando a única evidência é uma movimentação processual.

Preferir:

```json
{
  "signal_code": "PROPERTY_PENHORA_EVIDENCE",
  "severity": "HIGH",
  "confidence": 0.85,
  "evidence_text": "Foi identificada evidência processual relacionada a penhora."
}
```

Mensagem complementar:

> A confirmação de que a medida recai sobre determinado imóvel exige validação registral e documental.

---

# 36. Signal Engine

O mecanismo deve detectar evidências, não emitir parecer jurídico.

Fluxo:

```text
Processo
   ↓
Movimentos
   ↓
Assuntos
   ↓
Classes
   ↓
Regras
   ↓
Sinais
```

---

# 37. Regras de sinais

Tabela conceitual:

```text
judicial_signal_rule
```

Campos:

```text
id
signal_code
name
description
category
severity
matching_type
terms
enabled
version
valid_from
valid_until
```

As regras precisam ser versionadas.

---

# 38. Exemplo de regra

```text
signal_code:
PENHORA

terms:
["penhora", "penhorado", "penhorada"]

category:
PATRIMONIAL

severity:
HIGH
```

---

# 39. Distinção: processo x imóvel

Este é um requisito crítico.

Encontrar:

```text
Processo de execução
```

e:

```text
Movimentação mencionando penhora
```

não significa automaticamente:

```text
O imóvel analisado está penhorado.
```

É necessária correlação com o imóvel e confirmação documental.

---

# 40. O que a pesquisa judicial pode indicar

Dependendo dos dados efetivamente disponíveis:

- execução;
- execução fiscal;
- cobrança;
- penhora;
- arresto;
- indisponibilidade mencionada no processo;
- alienação fiduciária;
- hipoteca;
- usucapião;
- desapropriação;
- inventário;
- partilha;
- falência;
- recuperação judicial;
- insolvência;
- conflitos patrimoniais;
- ações trabalhistas;
- outros sinais processuais relevantes.

A disponibilidade de cada informação depende dos dados fornecidos pela fonte.

---

# 41. O que exige confirmação registral/documental

A API judicial não substitui:

- matrícula atualizada;
- certidão de ônus reais;
- Registro de Imóveis;
- certidão de indisponibilidade;
- documentos do processo;
- edital;
- demais certidões pertinentes.

Modelo conceitual:

```text
Pesquisa Judicial
       ↓
Evidência Processual
       ↓
Correlação com pessoa/imóvel
       ↓
Validação documental
       ↓
Conclusão jurídica/documental
```

---

# 42. Correlação futura com imóvel

O modelo deve estar preparado para:

```text
matrícula
owner
CPF/CNPJ
address
municipality
comarca
lote
quadra
inscrição imobiliária
```

Uma primeira versão pode trabalhar principalmente com:

```text
CPF/CNPJ
nome
UF
```

Posteriormente:

```text
Pessoa
   +
Processo
   +
Imóvel
   +
Matrícula
```

---

# 43. Checklist de identificação

```text
☐ Proprietário identificado
☐ CPF/CNPJ identificado
☐ Possível homônimo
☐ Divergência cadastral
```

---

# 44. Checklist processual

```text
☐ Justiça Estadual
☐ Justiça Federal
☐ Justiça do Trabalho
☐ Justiça Superior
☐ Justiça Eleitoral
☐ Justiça Militar
```

---

# 45. Checklist patrimonial

```text
☐ Execução
☐ Execução fiscal
☐ Cobrança
☐ Penhora
☐ Arresto
☐ Indisponibilidade
☐ Alienação fiduciária
☐ Insolvência
☐ Falência
☐ Recuperação judicial
```

---

# 46. Checklist relacionado ao imóvel

```text
☐ Processo menciona imóvel
☐ Matrícula identificada
☐ Endereço identificado
☐ Proprietário coincide
☐ Necessidade de confirmação registral
```

---

# 47. Checklist de qualidade

```text
☐ Todas as fontes consultadas
☐ Timeouts registrados
☐ Erros registrados
☐ Fontes não suportadas identificadas
☐ Dados incompletos identificados
☐ Reanálise necessária
☐ Resultado truncado identificado
```

---

# 48. API — Health

```http
GET /health
```

Exemplo:

```json
{
  "status": "UP",
  "service": "judicial-api",
  "version": "1.0.0"
}
```

---

# 49. API — Tribunais

```http
GET /api/v1/judicial/tribunals
```

Exemplo:

```json
{
  "items": [
    {
      "code": "TJPR",
      "name": "Tribunal de Justiça do Paraná",
      "justice_type": "STATE",
      "uf": "PR",
      "enabled": true
    }
  ]
}
```

---

# 50. API — Capabilities

```http
GET /api/v1/judicial/capabilities
```

Exemplo:

```json
{
  "provider": "DATAJUD",
  "tribunals": [
    {
      "tribunal": "TJPR",
      "supports": {
        "name": true,
        "cpf": true,
        "cnpj": true,
        "process_number": true
      }
    }
  ]
}
```

---

# 51. API — Pesquisa

```http
POST /api/v1/judicial/search
```

---

# 52. API — Consulta de pesquisa

```http
GET /api/v1/judicial/search/{search_id}
```

---

# 53. API — Fontes

```http
GET /api/v1/judicial/search/{search_id}/sources
```

Permite visualizar individualmente:

```text
TJPR → SUCCESS
TJSP → TIMEOUT
TRF4 → SUCCESS
TRT9 → SUCCESS
```

---

# 54. API — Retry

```http
POST /api/v1/judicial/search/{search_id}/retry
```

---

# 55. API — Providers

```http
GET /api/v1/judicial/providers/status
```

Exemplo:

```json
{
  "providers": [
    {
      "provider": "DATAJUD",
      "status": "AVAILABLE"
    }
  ]
}
```

---

# 56. Banco de dados

Schema:

```text
sch_judicial
```

Tabelas:

```text
judicial_provider
judicial_endpoint
judicial_credential
judicial_search
judicial_search_source
judicial_process
judicial_process_party
judicial_process_subject
judicial_process_movement
judicial_signal
judicial_signal_rule
judicial_error
judicial_search_event
```

---

# 57. judicial_provider

```text
id
code
name
enabled
version
created_at
updated_at
```

Exemplo:

```text
DATAJUD
```

---

# 58. judicial_endpoint

```text
id
provider
tribunal_code
tribunal_name
justice_type
uf
alias
base_url
search_path
enabled
priority

supports_process_number
supports_name
supports_cpf
supports_cnpj
supports_subject
supports_class
supports_movements
supports_court

timeout_ms
retry_count
max_page_size
max_pages
concurrency_group

configuration_version
last_validation_at

created_at
updated_at
```

---

# 59. Credenciais

Tabela:

```text
judicial_credential
```

Campos:

```text
id
provider
credential_type
encrypted_value
active
valid_from
valid_until
created_at
updated_at
```

A chave deve ser criptografada em repouso.

A chave utilizada para criptografia não deve ficar dentro da mesma tabela/banco em texto aberto.

---

# 60. judicial_search

```text
id
correlation_id
request_hash
status
execution_mode

requested_at
started_at
finished_at
duration_ms

total_sources
successful_sources
failed_sources
unsupported_sources

reanalysis_recommended
reanalysis_reason

created_at
```

---

# 61. judicial_search_source

```text
id
search_id
endpoint_id
provider
tribunal
status
http_status

started_at
finished_at
duration_ms

pages
result_count
attempts

error_code
error_message
retryable
```

---

# 62. judicial_process

```text
id
search_id
provider
tribunal
justice_type
process_number
court
jurisdiction

class_code
class_name

priority
electronic
system

last_movement_at

source_identifier
raw_hash

created_at
updated_at
```

Chave lógica:

```text
provider + tribunal + process_number
```

---

# 63. judicial_process_party

```text
id
process_id
name
document
document_type
role
party_type
representation
source_identifier
```

---

# 64. judicial_process_subject

```text
id
process_id
code
name
source_identifier
```

---

# 65. judicial_process_movement

```text
id
process_id
movement_date
code
description
complement
court
status
source_identifier
movement_hash
```

---

# 66. judicial_signal

```text
id
process_id
search_id
signal_code
severity
confidence
evidence_text
evidence_type
source_identifier
rule_version
created_at
```

---

# 67. judicial_error

```text
id
search_id
source_id
provider
tribunal
code
message
technical_message
retryable
http_status
correlation_id
occurred_at
```

A mensagem técnica deve ter acesso restrito.

---

# 68. judicial_search_event

Eventos:

```text
SEARCH_CREATED
SOURCE_SELECTED
SOURCE_STARTED
SOURCE_RETRY
SOURCE_SUCCESS
SOURCE_FAILED
NORMALIZATION_COMPLETED
SIGNAL_ANALYSIS_COMPLETED
SEARCH_COMPLETED
REANALYSIS_REQUESTED
```

---

# 69. Auditoria

Toda pesquisa deve registrar:

```text
search_id
correlation_id
critérios
fontes selecionadas
fontes ignoradas
motivos
timestamps
duração
status
resultados
erros
versão do provider
versão do normalizador
versão das regras de sinais
```

---

# 70. Idempotência

Calcular:

```text
request_hash
```

a partir dos critérios relevantes da consulta.

Isso permite identificar pesquisas equivalentes e controlar reprocessamentos.

---

# 71. Observabilidade

Logs estruturados:

```text
search_id
correlation_id
provider
tribunal
event
duration
status
```

Nunca registrar:

- API key;
- senha;
- CPF completo;
- CNPJ completo;
- payload sensível desnecessário.

---

# 72. Métricas

Métricas mínimas:

```text
searches_total
searches_completed
searches_partial
searches_failed

provider_errors
provider_timeouts
provider_latency

processes_found
signals_found

retries_total
unsupported_queries
```

---

# 73. Segurança

Implementar:

- autenticação;
- autorização;
- rate limiting;
- validação de entrada;
- limite de payload;
- limite de paginação;
- timeout;
- proteção contra consultas abusivas;
- credenciais criptografadas;
- secrets externos;
- auditoria;
- mascaramento de dados.

A API key nunca deve estar:

- no frontend;
- no Git;
- em arquivos de configuração versionados;
- em logs;
- em respostas.

---

# 74. Interface do Provider

Interface conceitual:

```text
JudicialProvider
```

Operações mínimas:

```text
search()
get_capabilities()
health_check()
normalize()
```

Implementação inicial:

```text
DataJudProvider
```

---

# 75. Benefício da abstração

Hoje:

```text
DataJudProvider
```

Futuramente:

```text
DataJudProvider
ProviderB
ProviderC
RegistryProvider
```

O contrato externo da API permanece estável.

---

# 76. Configuração de tribunais

Tribunais não devem ser hardcoded em dezenas de arquivos.

Exemplo:

```text
TJPR
Tribunal de Justiça do Paraná
STATE
PR
DATAJUD
```

Configuração centralizada.

---

# 77. Aliases

Exemplo:

```text
TJPR
Tribunal de Justiça do Paraná
Tribunal de Justiça do Estado do Paraná
```

Todos devem apontar para:

```text
TJPR
```

Aliases devem ficar no banco/configuração.

---

# 78. Exemplo completo de fluxo

Entrada:

```json
{
  "cpf": "12345678900",
  "uf": "PR",
  "include_movements": true
}
```

Fluxo:

```text
1. Validar CPF
       ↓
2. Selecionar tribunais
       ↓
3. Verificar capabilities
       ↓
4. Criar search_id
       ↓
5. Disparar fontes em paralelo
       ↓
6. Consultar DataJud
       ↓
7. Paginar
       ↓
8. Normalizar
       ↓
9. Deduplicar
       ↓
10. Detectar sinais
       ↓
11. Persistir
       ↓
12. Registrar erros
       ↓
13. Calcular COMPLETED / EMPTY / PARTIAL / FAILED
       ↓
14. Determinar reanálise
       ↓
15. Retornar resposta
```

---

# 79. Exemplo de resultado com sinal

```json
{
  "search_id": "uuid",
  "status": "COMPLETED",
  "processes": [
    {
      "process_number": "0000000-00.0000.0.00.0000",
      "tribunal": "TJPR",
      "justice_type": "STATE",
      "parties": [],
      "subjects": [],
      "movements": []
    }
  ],
  "signals": [
    {
      "signal_code": "PROPERTY_PENHORA_EVIDENCE",
      "severity": "HIGH",
      "confidence": 0.85,
      "evidence_text": "Foi identificada evidência processual relacionada a penhora.",
      "evidence_type": "MOVEMENT"
    }
  ]
}
```

---

# 80. Exemplo de resultado parcial

```json
{
  "search_id": "uuid",
  "status": "PARTIAL",
  "completeness": {
    "requested_sources": 4,
    "successful_sources": 3,
    "failed_sources": 1,
    "unsupported_sources": 0
  },
  "sources": [
    {
      "tribunal": "TJPR",
      "status": "SUCCESS"
    },
    {
      "tribunal": "TJSC",
      "status": "SUCCESS"
    },
    {
      "tribunal": "TRF4",
      "status": "SUCCESS"
    },
    {
      "tribunal": "TJSP",
      "status": "TIMEOUT",
      "error": {
        "code": "PROVIDER_TIMEOUT",
        "retryable": true
      }
    }
  ],
  "reanalyze": {
    "recommended": true,
    "reason": "TRIBUNAL_UNAVAILABLE",
    "sources_affected": [
      "TJSP"
    ]
  }
}
```

---

# 81. Mensagens amigáveis

## Processo encontrado

> Foi localizado processo envolvendo uma parte relacionada à pessoa pesquisada.

## Execução

> Foi identificada evidência processual compatível com execução.

## Penhora

> Foi encontrada evidência processual relacionada a penhora. É necessário confirmar se a medida recai sobre este imóvel.

## Homônimo

> Foi localizado processo com nome semelhante, mas não há evidência suficiente para confirmar que pertence à pessoa pesquisada.

## Pesquisa incompleta

> Alguns tribunais não responderam. A ausência de processos nesses tribunais não pode ser considerada uma conclusão.

## Nenhum resultado

> Os tribunais consultados responderam normalmente e não foram encontrados processos compatíveis com os critérios informados.

## Resultado limitado

> A consulta atingiu o limite configurado e pode haver resultados adicionais.

---

# 82. Testes unitários

Cobrir pelo menos:

```text
query building
capabilities
normalization
pagination
retry
timeout
rate limit
error mapping
deduplication
homonyms
status calculation
signal detection
signal rule versioning
```

---

# 83. Testes de integração

Cobrir:

```text
FastAPI
PostgreSQL
migrations
persistence
concurrency
retry
timeout
audit
reanalysis
```

---

# 84. Testes reais

Os testes reais contra o DataJud não devem fazer parte da suíte padrão.

Exemplo:

```bash
RUN_REAL_DATAJUD_TESTS=true pytest tests/real
```

Devem exigir configuração explícita.

---

# 85. Smoke test nacional

Testar representantes de:

```text
Superior
Federal
Estadual
Trabalhista
Eleitoral
Militar
```

Resultado:

```text
TOTAL
SUCCESS
EMPTY
TIMEOUT
ERROR
UNSUPPORTED
```

---

# 86. Testes sem credencial

A suíte local deve funcionar sem API key real utilizando mocks/fakes do provider.

---

# 87. Documentação necessária

O projeto deve possuir documentação para:

```text
README
Architecture
API
Configuration
Providers
Tribunals
Database
Security
Errors
Signals
Testing
Operations
Troubleshooting
Compliance
```

---

# 88. Compliance e condições de uso

A utilização de uma API pública não deve ser interpretada automaticamente como autorização irrestrita para qualquer finalidade.

Antes de produção, devem ser revisadas as normas e condições atuais do CNJ/DataJud, especialmente quanto a:

- finalidade de uso;
- tratamento de dados;
- armazenamento;
- redistribuição;
- modificação;
- criação de produtos derivados;
- uso comercial;
- requisitos de identificação/citação da fonte;
- limitações de responsabilidade;
- atualização e confiabilidade dos dados.

A arquitetura deve permitir desabilitar ou substituir o provider caso as condições de uso não sejam compatíveis com o produto final.

Também não se deve tratar o DataJud como garantia absoluta de completude, atualidade ou correção dos dados.

---

# 89. Requisito de revisão oficial antes do desenvolvimento

Antes de implementar qualquer integração específica:

1. consultar o catálogo oficial atual;
2. validar endpoints;
3. validar aliases;
4. validar autenticação;
5. validar campos pesquisáveis;
6. validar operadores;
7. validar paginação;
8. validar limites;
9. validar formato de resposta;
10. validar tratamento de processos sigilosos;
11. validar condições de uso;
12. registrar limitações conhecidas.

Se uma capacidade não puder ser comprovada:

```text
UNSUPPORTED_SEARCH_CRITERIA
```

ou:

```text
PENDING_VALIDATION
```

Nunca assumir.

---

# 90. Plano de implementação

## Fase 1 — Foundation

- estrutura do projeto;
- configuração;
- logging;
- tratamento de erros;
- health check.

## Fase 2 — Database

- schema;
- migrations;
- entidades;
- índices;
- constraints.

## Fase 3 — Provider

- interface;
- registry;
- DataJudProvider.

## Fase 4 — Tribunais

- catálogo;
- aliases;
- capabilities;
- endpoints.

## Fase 5 — Pesquisa

- query builder;
- paginação;
- orchestrator;
- concorrência.

## Fase 6 — Resiliência

- timeout;
- retry;
- backoff;
- rate limit;
- limites.

## Fase 7 — Normalização

- processos;
- partes;
- assuntos;
- movimentos.

## Fase 8 — Sinais

- regras;
- versionamento;
- evidências.

## Fase 9 — Persistência

- pesquisas;
- fontes;
- processos;
- sinais;
- erros;
- eventos.

## Fase 10 — Reanálise

- retry manual;
- retry de fontes falhas;
- histórico.

## Fase 11 — REST API

- endpoints;
- documentação OpenAPI;
- autenticação.

## Fase 12 — Observabilidade

- logs;
- métricas;
- auditoria.

## Fase 13 — Testes

- unitários;
- integração;
- mocks;
- smoke;
- testes reais opcionais.

## Fase 14 — Hardening

- segurança;
- limites;
- performance;
- concorrência;
- revisão de compliance.

---

# 91. Critérios de aceite

O módulo será considerado funcional quando:

## Arquitetura

- [ ] estiver isolado;
- [ ] possuir REST API;
- [ ] possuir provider abstraction;
- [ ] possuir DataJudProvider;
- [ ] estiver preparado para futuros providers.

## Nacional

- [ ] catálogo nacional validado;
- [ ] tribunais configuráveis;
- [ ] aliases configuráveis;
- [ ] capabilities configuráveis.

## Segurança

- [ ] API key protegida;
- [ ] credenciais criptografadas;
- [ ] segredo externo à aplicação;
- [ ] nenhum segredo no Git;
- [ ] nenhum segredo no frontend;
- [ ] nenhum segredo nos logs.

## Pesquisa

- [ ] pesquisa multi-tribunal;
- [ ] execução paralela;
- [ ] concorrência limitada;
- [ ] timeout;
- [ ] retry;
- [ ] paginação;
- [ ] limites.

## Dados

- [ ] processos;
- [ ] partes;
- [ ] assuntos;
- [ ] movimentos;
- [ ] deduplicação.

## Jurídico

- [ ] sinais;
- [ ] evidências;
- [ ] regras versionadas;
- [ ] distinção entre processo e imóvel;
- [ ] tratamento de homônimos.

## Erros

- [ ] erros normalizados;
- [ ] COMPLETED;
- [ ] EMPTY;
- [ ] PARTIAL;
- [ ] FAILED;
- [ ] reanálise.

## Auditoria

- [ ] histórico;
- [ ] correlation ID;
- [ ] eventos;
- [ ] rastreabilidade.

## Observabilidade

- [ ] logs;
- [ ] métricas;
- [ ] latência;
- [ ] erros;
- [ ] retries.

## Testes

- [ ] unitários;
- [ ] integração;
- [ ] mocks;
- [ ] testes reais opcionais;
- [ ] smoke nacional.

## Documentação

- [ ] README;
- [ ] arquitetura;
- [ ] API;
- [ ] banco;
- [ ] configuração;
- [ ] segurança;
- [ ] troubleshooting;
- [ ] compliance.

---

# 92. Princípios arquiteturais

### 1. Provider independente

O domínio não conhece detalhes de cada fornecedor.

### 2. Configuração em banco

Tribunais, aliases, endpoints e capacidades devem ser parametrizáveis.

### 3. Falha isolada

Um tribunal indisponível não deve derrubar os demais.

### 4. Resultado honesto

`EMPTY` não pode ser usado quando a consulta ficou incompleta.

### 5. Evidência ≠ conclusão jurídica

Sinais processuais não substituem análise documental ou registral.

### 6. Segurança por padrão

Credenciais nunca devem aparecer no código, frontend ou logs.

### 7. Rastreabilidade

Toda pesquisa precisa ser auditável.

### 8. Reprocessamento

Falhas transitórias devem poder ser reprocessadas.

### 9. Evolução

A arquitetura deve permitir adicionar novos providers sem quebrar o contrato.

### 10. Documentação oficial como fonte de verdade

Capacidades específicas do provider devem ser confirmadas antes de serem implementadas.

---

# 93. Visão final

O resultado esperado é uma API judicial genérica:

```text
                    ┌─────────────────────┐
                    │   Aplicação cliente  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    Judicial API     │
                    ├─────────────────────┤
                    │ Search              │
                    │ Orchestration       │
                    │ Normalization       │
                    │ Signals             │
                    │ Persistence         │
                    │ Audit               │
                    │ Observability       │
                    └──────────┬──────────┘
                               │
                 ┌─────────────┴─────────────┐
                 │                           │
                 ▼                           ▼
          ┌───────────────┐          ┌───────────────┐
          │ DataJud       │          │ Future Provider│
          │ Provider      │          │               │
          └───────┬───────┘          └───────────────┘
                  │
          ┌───────┼────────┐
          ▼       ▼        ▼
        TJPR    TJSP     TRF4
          │       │        │
          └───────┼────────┘
                  ▼
             Normalização
                  │
          ┌───────┴────────┐
          ▼                ▼
       Processos        Sinais
          │                │
          └───────┬────────┘
                  ▼
             Resultado
                  │
                  ▼
             Reanálise
```

## Princípio jurídico fundamental

A API deve ser entendida como uma **camada de pesquisa e evidência processual**.

Ela pode indicar:

> “Foi localizada evidência processual compatível com penhora.”

Ela não deve afirmar automaticamente:

> “O imóvel está penhorado.”

A confirmação de um gravame sobre um imóvel exige correlação adequada e, quando aplicável, validação por matrícula, Registro de Imóveis, certidões e documentos processuais.

---

# 94. Checklist final de implementação

```text
[ ] Revisar documentação oficial DataJud
[ ] Revisar catálogo nacional
[ ] Revisar condições de uso
[ ] Criar arquitetura
[ ] Criar banco
[ ] Criar provider abstraction
[ ] Criar DataJudProvider
[ ] Criar registry
[ ] Cadastrar tribunais
[ ] Cadastrar aliases
[ ] Cadastrar capabilities
[ ] Implementar credenciais seguras
[ ] Implementar busca
[ ] Implementar paginação
[ ] Implementar concorrência
[ ] Implementar timeout
[ ] Implementar retry
[ ] Implementar normalização
[ ] Implementar deduplicação
[ ] Implementar persistência
[ ] Implementar erros
[ ] Implementar sinais
[ ] Implementar auditoria
[ ] Implementar observabilidade
[ ] Implementar reanálise
[ ] Implementar REST API
[ ] Implementar testes
[ ] Executar smoke tests
[ ] Executar revisão de segurança
[ ] Executar revisão de compliance
[ ] Executar revisão final
```

---

## Referências oficiais

- DataJud — API Pública: https://datajud-wiki.cnj.jus.br/api-publica/
- DataJud — Acesso: https://datajud-wiki.cnj.jus.br/api-publica/acesso/
- DataJud — Endpoints: https://datajud-wiki.cnj.jus.br/api-publica/endpoints/
- DataJud — Exemplos: https://datajud-wiki.cnj.jus.br/api-publica/exemplos/
- DataJud — Glossário: https://datajud-wiki.cnj.jus.br/api-publica/glossario/

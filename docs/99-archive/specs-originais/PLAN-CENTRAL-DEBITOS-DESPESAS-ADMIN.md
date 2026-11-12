# PLAN — Central de Débitos, Despesas e Parametrização Administrativa

> **Status:** PLANEJAMENTO (análise + arquitetura). **Nada implementado.** Nenhum código, migration,
> dado, commit, consulta externa ou scraping foi executado ao produzir este documento. As consultas
> web feitas serviram **apenas** para descobrir a existência de portais oficiais públicos — nenhum
> débito real foi consultado, nenhum CAPTCHA/autenticação contornado.
>
> **Base:** código efetivo em HEAD `7f61667` (branch `main`), confirmado por varredura do repositório.
> Complementa (não duplica): `MATRIZ-CUSTOS-TRIBUTOS-EMOLUMENTOS.md`, `MATRIZ-OPPORTUNITY-ID.md`,
> `ROADMAP-EXECUTION.md`, `FEATURE-INVENTORY.md`, `PRODUCT-DASHBOARD.md`, `SPEC-HARD-STOPS.md`,
> `REVISAO-ANOTACOES-LEILAO.md`.

---

## 1. Resumo executivo

Objetivo: criar uma **Central de Débitos e Despesas** (identificação, consulta, apuração e estimativa
de todos os passivos/custos de um imóvel/oportunidade) e um **Módulo Administrativo** que permita ao
responsável configurar municípios, tipos de débito, fontes, parâmetros financeiros, regras de
estimativa e alertas **sem alterar código**.

Princípios: **arquitetura extensível por adaptadores** (o núcleo não conhece portais); **determinístico
primeiro** (LLM só para interpretar documento não estruturado, com evidência, nunca para inventar
valor); **parâmetros de negócio versionados e administráveis**; **CONFIRMADO ≠ ESTIMADO ≠ INFORMADO**;
**ausência de resultado ≠ ausência de débito**; preservação integral do que já existe (modelos `Debt`/
`Cost`, endpoints, 27 `canonical_key`, 633/V1–V9, Central Jurídica).

A entrega é **incremental (Etapas A–F)**. Nenhuma integração automática com portal municipal será
construída sem validação de termos de uso, viabilidade técnica e autorização explícita; o **fallback
manual** (que já existe) permanece como caminho sempre válido.

**Dependência estratégica:** o Módulo Administrativo exige **autenticação/RBAC**, hoje inexistente
(ver `FEATURE-INVENTORY` G9). Área administrativa **não** pode ser exposta sem proteção.

---

## 2. Diagnóstico do que já existe (código efetivo)

| Capacidade atual | Onde | Observação |
|---|---|---|
| `Debt` (dívidas) | `models.py:311` | **Flat:** `category`, `creditor`, `amount`, `reference_date`, `status` (default `PENDENTE`), `evidence_id`. **Não tem** município, tipo canônico, competência, split original/atualizado, juros/multa/correção, grau de confiabilidade, método de obtenção. |
| `Cost` (custos) | `models.py:300` | `category`, `description`, `amount`, `recurring`. |
| CRUD dívidas/custos | `main.py:655–751` (`/custos`, `/dividas`) | Com evento + histórico; recalcula `build_finance`. |
| Registro manual de débito municipal | `main.py:1980` (`/due-diligence/prefeitura/debito`) | **Reusa `Debt`** (não duplica custo); marca frente `PREFEITURA`; reflete pendência no checklist `RESPONSABILIDADE_DEBITOS`. |
| Custos pós-arrematação | `PostAuctionCost` + `/pos-arrematacao/custos` | Previsto/realizado/pago; resumo consistente com `build_finance`. |
| Consumo financeiro de dívidas | `finance.py` / `services.build_finance` | `Debt` com `status != QUITADO` soma no breakdown `debitos`; `COST_KEYS` fixas (`itbi`, `registro`, `condominio`, `iptu`, `debitos`, …). |
| Frente PREFEITURA (due diligence) | `services._front_summary_prefeitura` | Filtra `Debt` por `IPTU`/`PREFEITURA`; `NAO_CONFIGURADO` sem `prefeitura_api_base_url`. |
| Config de integração | `config.py` | `prefeitura_api_base_url`/`registro_imoveis_base_url` = `None` por padrão; **nenhum cliente HTTP municipal existe**. |
| Evidência/rastreabilidade | `Evidence`/`EvidenceLink`, `DomainEvent`/`EntityHistory` | Reutilizável diretamente pela Central. |
| Credenciais seguras | `secrets_crypto.py` (Fernet, falha-fechada) | Reutilizável para credenciais de portais. |

**Conclusão:** há uma base sólida mas **genérica demais** para débitos municipais ricos. A Central
não substitui `Debt`/`Cost`: **estende** o modelo (aditivo), preserva os endpoints atuais e os promove
a um domínio normalizado, com município, tipo canônico, origem/confiabilidade e separação
original×atualizado — sem quebrar o que o motor financeiro já consome.

---

## 3. Inventário de hardcodes (classificação A–E)

> Classes: **A** parâmetro de negócio (admin) · **B** operacional (config técnica segura; pode ou não
> ir à admin) · **C** constante técnica (fica no código) · **D** segredo (cofre) · **E** regra
> estrutural (lógica no código; valores variáveis podem ser configuráveis).

| Item | Onde | Classe | Destino proposto |
|---|---|---|---|
| `MIN_SAMPLE = 7` (amostra de mercado) | `market.py:9` | **A** | Catálogo de parâmetros (global/por município) |
| `HIGH_DISPERSION_CV = 0.30` | `market.py:11` | **A** | Catálogo de parâmetros |
| `required = index <= 15` (criticidade do checklist) | `checklist.py:42` | **A/E** | Parâmetro + checklist dinâmico (Onda 4) |
| Severidade `ALTA`/`MEDIA` por estado | `risk_engine.py` | **A/E** | Mapa configurável de severidade |
| Precedência de veredito (CRÍTICA→DESFAVORÁVEL) | `verdict_engine.py` | **E** | Estrutura fica; limiares de score (futuro) configuráveis |
| `POST_AUCTION_DEFAULT_STAGES` (16 etapas) | `services.py:551` | **A/B** | Catálogo administrável (template de etapas) |
| Pesos RAG `0.7/0.3`, limites `8/50` | `config.py` | **B** | Config técnica (pode espelhar na admin como leitura) |
| `extraction_min_chars=200`, `_per_kb=1.0` | `config.py` | **B** | Config técnica |
| `due_diligence_cache_hours=24` | `config.py` | **B** | Admin (afeta custo/frequência de consulta) |
| `PER_ITEM_LIMIT=4`, `MAX_TOTAL_CHUNKS=24` | `rag/checklist_retrieval.py` | **B** | Config técnica |
| `ZERO`/`HUNDRED`/fórmulas | `finance.py` | **C** | Permanece no código |
| `DD_FRENTES`, `CHECKLIST_STATES`, `VERDICT_STATES`, `LEGAL_CONTEXTS`, matriz de transições | `models.py`/`workflow_rules.py` | **E** | Estrutura no código |
| `PORTAL_SECRET_KEY`, `PORTAL_ADMIN_TOKEN`, API keys | `config.py` | **D** | Cofre/env (nunca em tela) |

**Achado positivo:** **não há alíquota fiscal hardcoded** (ITBI/IR/emolumentos/FUNREJUS). O motor
financeiro já recebe percentuais como **input**, coerente com a regra "nada fiscal sem fonte oficial +
vigência" (`MATRIZ-CUSTOS-TRIBUTOS-EMOLUMENTOS` e `REVISAO-ANOTACOES-LEILAO §5`). Logo, a Central
**introduz** parâmetros fiscais parametrizados — não migra constantes existentes.

**Diretriz:** eliminar hardcodes **de negócio** (classe A), avaliar os **B** caso a caso, e **não**
transformar C/E em banco. O objetivo é acabar com "número mágico de negócio no código", não tornar o
sistema dinâmico demais.

---

## 4. Matriz de parâmetros administráveis (inicial)

| Chave (proposta) | Categoria | Tipo | Abrangência | Default | Observação |
|---|---|---|---|---|---|
| `mercado.amostra_minima` | Mercado | int | global/município | 7 | hoje `MIN_SAMPLE` |
| `mercado.cv_dispersao_alta` | Mercado | decimal | global | 0.30 | hoje `HIGH_DISPERSION_CV` |
| `condominio.valor_mensal_referencia` | Estimativa | decimal | município/condomínio/tipologia | — | estimativa condominial |
| `condominio.periodo_presumido_meses` | Estimativa | int | global/município | — | estimativa condominial |
| `condominio.margem_seguranca_pct` | Estimativa | decimal | global | — | estimativa condominial |
| `condominio.despesa_extraordinaria` | Estimativa | decimal | condomínio | — | opcional |
| `checklist.idade_alerta_1_anos` | Alertas | int | global | 10 | exemplo inicial |
| `checklist.idade_alerta_2_anos` | Alertas | int | global | 15 | exemplo inicial |
| `checklist.idade_nivel_alerta` | Alertas | enum | global | ATENCAO | nível do alerta |
| `financeiro.itbi_pct` | Fiscal | decimal | município + vigência | — | **só com fonte oficial** |
| `financeiro.emolumentos_registro` | Fiscal | tabela | UF/ato + vigência | — | **só com fonte oficial** |
| `financeiro.corretagem_venda_pct` | Financeiro | decimal | global | — | premissa de saída |
| `due_diligence.cache_horas` | Operacional | int | global | 24 | hoje em config |
| `posarrematacao.template_etapas` | Operacional | lista | global | 16 etapas | hoje `POST_AUCTION_DEFAULT_STAGES` |

> Esta é a matriz **inicial**; o catálogo (§7.2) é extensível. Cada parâmetro carrega vigência, versão
> e abrangência (hierarquia de precedência em §7.2). **Parâmetros fiscais nunca entram sem fonte
> oficial + vigência** (decisão de negócio — §21).

---

## 5. Catálogo inicial de débitos e despesas

> Catálogo **administrável** (não enum fixo no código). Cada tipo tem: `codigo`, `grupo`, `natureza`,
> `confirmavel_em_fonte` (bool), `impacta_financeiro` (bool), `canonical_cost_key` (mapeamento para o
> `COST_KEYS` do motor financeiro).

**Grupo A — Débitos municipais** (natureza: dívida existente/potencial)
- `IPTU`, `TAXA_LIXO` (TCL), `TAXAS_MUNICIPAIS`, `DIVIDA_ATIVA_MUNICIPAL`, `ISSQN` (quando incide),
  `CONTRIBUICAO_MELHORIA`, `PARCELAMENTO_MUNICIPAL`.

**Grupo B — Débitos condominiais** (natureza: obrigação propter rem)
- `CONDOMINIO_ORDINARIO`, `CONDOMINIO_EXTRAORDINARIO`, `MULTA_CONDOMINIAL`, `JUROS_CONDOMINIAIS`,
  `CORRECAO_CONDOMINIAL`, `ACORDO_CONDOMINIAL`.

**Grupo C — Custos de aquisição/regularização** (natureza: custo operacional, não "dívida")
- `ITBI`, `REGISTRO`, `ESCRITURA`, `CERTIDOES`, `EMOLUMENTOS`, `REGULARIZACAO` (habite-se/averbação),
  `CUSTOS_JURIDICOS`, `DESOCUPACAO`, `REFORMA`, `CARREGAMENTO`.

**Grupo D — Concessionárias/utilidades** (natureza: distinguir dívida pessoal × vinculada ao imóvel)
- `AGUA`, `ENERGIA`, `GAS` — **marcados por padrão como dívida pessoal do ocupante**, só viram passivo
  do imóvel com base legal/evidência (ver `REVISAO-ANOTACOES-LEILAO §5`).

**Classificação transversal de cada lançamento (natureza):**
`DIVIDA_EXISTENTE` · `OBRIGACAO_POTENCIAL` · `CUSTO_AQUISICAO` · `ESTIMATIVA_OPERACIONAL`.
Isso impede somar naturezas diferentes (§9) e separar "o que é passivo" de "o que é custo da operação".

---

## 6. Matriz dos quatro municípios e fontes de consulta

> Levantamento de **existência de portais oficiais públicos** (web search; nenhuma consulta de débito
> real foi feita). "API oficial documentada" **não** foi confirmada para nenhum — exige investigação
> dedicada (e validação de termos de uso) antes de qualquer automação.

| Município | Portal oficial identificado | IPTU/débito imobiliário | Dívida ativa | Identificador | Classificação da fonte |
|---|---|---|---|---|---|
| **Curitiba/PR** | `iptu-dam.curitiba.pr.gov.br`, `financas.curitiba.pr.gov.br` | Sim (consulta/DAM pela internet) | A investigar | Inscrição Imobiliária+Sublote **ou** Indicação Fiscal (CPF/CNPJ p/ endereço) | **Portal com consulta (potencialmente automatizável)** |
| **São José dos Pinhais/PR** | `financas.sjp.pr.gov.br` (portalGateway), Semfi | Sim (portal de finanças) | A investigar | A investigar (inscrição) | **Portal com consulta (a investigar a fundo)** |
| **Fazenda Rio Grande/PR** | `fazendariogrande.pr.gov.br` (Divisão de Arrecadação); possível `atende.net` | Sim (IPTU/2ª via) | A investigar | A investigar | **Portal com consulta (possível plataforma atende.net)** |
| **Assis/SP** | `tributacao.assis.sp.gov.br` ("Sistema de Arrecadação") | Sim (consulta débito imobiliário) | A investigar | A investigar | **Portal com consulta (NÃO confundir com a capital SP)** |

**Taxonomia de fonte (para cada município × tipo de débito):** `API_OFICIAL` · `SERVICO_OFICIAL_
DOCUMENTADO` · `PORTAL_CONSULTA_MANUAL` · `PORTAL_POTENCIALMENTE_AUTOMATIZAVEL` · `DEPENDE_AUTENTICACAO`
· `INDISPONIVEL` · `NAO_INVESTIGADA`.

**Estado atual honesto:** todos os quatro = `PORTAL_POTENCIALMENTE_AUTOMATIZAVEL` para IPTU; **dívida
ativa, certidões e API oficial = `NAO_INVESTIGADA`** (requerem análise dedicada de viabilidade e termos
de uso). A cobertura é **independente por município e por tipo de débito** (Curitiba pode ter IPTU +
dívida ativa; outro, só IPTU).

---

## 7. Viabilidade de API, integração e automação por município

> **Nenhuma automação será construída sem:** (1) confirmação de API/serviço oficial OU avaliação de
> que a automação de portal é **permitida pelos termos de uso** e tecnicamente sustentável; (2)
> autorização explícita; (3) credenciais em cofre. **Scraping não é a primeira escolha**; CAPTCHA/
> autenticação **nunca** são contornados.

**Prioridade de integração (por fonte):**
1. API oficial.
2. Serviço oficial documentado.
3. Integração disponibilizada pelo município.
4. Automação de portal oficial — **somente se permitida e sustentável**.
5. **Consulta manual assistida** (fallback sempre válido; é o estado atual).

**Avaliação preliminar (a confirmar em etapa dedicada):**
- **Curitiba:** portal IPTU-DAM estruturado por Inscrição/Indicação Fiscal — bom candidato a
  automação **se os termos permitirem**; requer o identificador fiscal do imóvel (nem sempre
  disponível no cadastro atual). Dívida ativa a investigar.
- **SJP / Fazenda Rio Grande:** plataformas de portal (possível `atende.net` em FRG); viabilidade de
  automação **não confirmada**; provável necessidade de parâmetros de acesso.
- **Assis/SP:** sistema de arrecadação próprio; viabilidade **não confirmada**.
- **Conclusão:** v1 entrega **registro manual assistido normalizado** para os 4 municípios; automação
  entra **por município** conforme viabilidade confirmada, sem bloquear a Central.

---

## 8. Arquitetura proposta (adaptadores e coletores)

Núcleo **não conhece** portais. Contratos (nomes alinhados ao padrão do projeto — ver
`judicial_client`/`judicial_integration`, `geocoding_client`):

- **`MunicipalDebtProvider`** (contrato/porta): `consultar(imovel_ctx, tipo_debito) -> DebtQueryResult`.
  Cada município/tipo implementa este contrato num **adaptador isolado**.
- **`MunicipalityRegistry`**: municípios cadastrados + cobertura (tabela, não lista no código).
- **`DebtTypeRegistry`**: catálogo de tipos de débito (§5), administrável.
- **`DebtSourceRegistry`**: fontes por município×tipo + classificação (§6) + situação operacional +
  data da última validação da fonte.
- **`DebtQueryService`** (orquestração): monta o plano de consulta a partir da oportunidade.
- **`DebtNormalizationService`**: normaliza resultado heterogêneo no modelo comum (§10 / spec §4.3).
- **`DebtEvidenceService`**: grava evidência (reusa `Evidence`/`EvidenceLink`).
- **`DebtReconciliationService`**: detecta divergência/duplicidade (não soma o mesmo lançamento).

**Camada de coletores (isolada, só quando necessária):** adaptadores de portal implementam o contrato
com timeout, retry controlado, rate limit, logs estruturados, versionamento do adaptador, tratamento
de indisponibilidade e **testes com respostas simuladas** (fixtures). O **domínio não depende** de
ferramenta de scraping — a dependência fica confinada ao coletor. Credenciais via `secrets_crypto`.

**Reuso-first:** `DomainEvent`/`EntityHistory` (trilha), `Evidence` (prova), `secrets_crypto` (cofre),
padrão de `due_diligence_fronts` (status por frente/fonte: `NAO_CONFIGURADO`/`CONSULTADO`/
`INDISPONIVEL`/`SEM_OCORRENCIA`/`NECESSITA_REVISAO`).

---

## 9. Avaliação de agentes especializados

**Recomendação: NÃO criar agentes LLM por município para coleta.** A coleta, identificação, cálculo e
normalização de valores são **determinísticos** — devem ser **adaptadores/serviços/workers**, não
agentes. Criar "Agente de IPTU de Curitiba" como LLM seria IA artificial sem valor e com risco de
inventar valores.

**Onde LLM agrega (com evidência + validação):** interpretar **documento não estruturado** já obtido
(ex.: PDF de certidão/carnê/espelho de IPTU anexado pelo usuário) para **extrair** campos — reutilizando
o pipeline de extração existente (`extraction.py`), que **exige referência/evidência** e nunca confirma
valor sem fonte. **LLM nunca** declara débito, inventa valor ou substitui consulta oficial.

**Decisão arquitetural por responsabilidade:**
| Responsabilidade | Solução recomendada |
|---|---|
| Consultar portal/fonte | Adaptador determinístico + coletor isolado |
| Normalizar resultado | Serviço determinístico |
| Calcular valor atualizado/estimativa | Serviço determinístico (fórmulas) |
| Extrair dados de PDF anexado | LLM com evidência (reusa `extraction.py`) |
| Orquestrar/agendar | Worker/serviço assíncrono |

---

## 10. Modelo de domínio proposto (aditivo e reversível)

> **Preserva `Debt`/`Cost` atuais.** O modelo comum normalizado é uma **evolução aditiva**. Duas
> opções a decidir (§21): **(A)** estender `Debt` com colunas nullable + novas tabelas de apoio;
> **(B)** nova tabela `property_debt` normalizada, com `Debt` mantido e migração de leitura. Recomendo
> **(A) para custos/dívidas simples + nova tabela para o resultado rico de consulta**, evitando quebrar
> o consumo financeiro atual.

Entidades novas propostas (todas com `opportunity_id` **nullable**, coerente com Gate 1 / `MATRIZ-
OPPORTUNITY-ID`; `NULL` = legado):

- **`municipality`** — município + cobertura ativa, situação operacional.
- **`debt_type`** — catálogo de tipos (§5): código, grupo, natureza, `canonical_cost_key`.
- **`debt_source`** — fonte por município×tipo: classificação, URL, auth requerida, limitações,
  `last_validated_at`, situação.
- **`property_debt`** (resultado normalizado) — campos da spec §4.3: imóvel, oportunidade, município,
  tipo, credor, identificador do débito, exercício/competência, vencimento, **valor_original**, juros,
  multa, correção, **valor_atualizado**, data-base do valor, situação, fonte, data/hora da consulta,
  `evidence_id`, método de obtenção, **grau_confiabilidade**, **status_validacao**, observações.
- **`debt_query`** (execução de consulta) — status por consulta: `PENDENTE`/`EM_EXECUCAO`/`CONCLUIDA`/
  `PARCIAL`/`INDISPONIVEL`/`REQUER_INTERVENCAO_MANUAL`/`ERRO`.
- **`condominium`** (cadastro futuro, §11) — nome, CNPJ, endereço, município, administradora, contatos,
  valor médio, histórico, características, evidências, fonte, atualização.
- **`debt_estimate`** (estimativa condominial, §11) — cenários e premissas versionadas.

**Invariantes:** separar `valor_original` de `valor_atualizado`; **nunca somar automaticamente**
lançamentos duplicados (reconciliação por identificador+competência); toda consulta grava fonte +
momento + confiabilidade; `CONFIRMADO ≠ ESTIMADO ≠ INFORMADO`.

---

## 11. Estratégia para estimativa condominial

**Duas estratégias complementares:**

### 11.1 Débito condominial confirmado
Documento/informação oficial → registra valor, competência, origem, evidência, data-base; permite
atualização. Natureza = `DIVIDA_EXISTENTE`, `status_validacao = CONFIRMADO`.

### 11.2 Estimativa parametrizada (quando não há informação confiável)
Modelo **configurável** (parâmetros da §4), nunca afirmando que existe dívida. Variáveis:
`valor_mensal_referencia`, `periodo_presumido_meses`, `margem_seguranca_pct`, `despesa_extraordinaria`,
mais variáveis de **contexto** (tipologia, padrão, região/município).

**Esclarecimento técnico obrigatório (exigido no prompt):** são **três coisas distintas** e o sistema
não pode confundi-las:
- **Idade do imóvel/empreendimento** — data de construção/entrega. Variável de **contexto** (influencia
  manutenção/incerteza), **não** prova de débito.
- **Idade do condomínio** — tempo de existência da convenção/instituição condominial.
- **Tempo de financiamento** — tempo do contrato de alienação fiduciária. **Nunca** é sinônimo de idade
  do imóvel nem de tempo de inadimplência.

→ A estimativa de inadimplência usa **`periodo_presumido_meses`** (parâmetro explícito), **não** deriva
de idade do imóvel nem do tempo de financiamento. Se só houver data de construção, ela entra como
contexto, não como passivo.

**Saída da estimativa:** valor mensal de referência, período considerado, critérios, valor estimado,
margem aplicada, e **cenários conservador/provável/otimista**. A UI identifica claramente
**VALOR CONFIRMADO ≠ VALOR ESTIMADO ≠ VALOR INFORMADO PELO USUÁRIO**. Uma estimativa **nunca** é
apresentada como passivo confirmado.

### 11.3 Cadastro futuro de condomínios
Modelo `condominium` preparado (§10) mas **não obrigatório na v1** — evolução posterior sem
reestruturar o domínio.

---

## 12. Integração com o Checklist Mestre (alertas de idade e exposição)

- **Preservar os 27 `canonical_key`** (não renomear/excluir/recriar). Confirmado: `checklist.py`
  mantém as 27 chaves; `RESPONSABILIDADE_DEBITOS` já recebe pendência da frente PREFEITURA.
- **Alerta de idade parametrizável:** regra nova, **configurável** (limite de idade, nível, texto,
  critérios, vigência, exceções — §4). Exemplos iniciais (não definitivos): ≥10 anos (alerta), ≥15
  anos (maior atenção). A regra respeita a **qualidade da informação de idade**: se a data de
  construção for desconhecida/estimada, **não** gera alerta conclusivo (coerente com `SPEC-HARD-STOPS`:
  nada conclusivo sem evidência).
- **Onde encaixar:** como **item aditivo** no checklist dinâmico (Onda 4) e/ou como alerta no dossiê —
  **sem** tocar as 27 chaves. A idade eleva **incerteza** de manutenção/reforma/passivos, registrada
  **separada** de débitos efetivamente identificados (nunca misturar incerteza com dívida confirmada).

---

## 13. Integração com o motor financeiro

- O motor (`finance.py`/`build_finance`) continua a **fonte** do cálculo; a Central **alimenta** dados
  estruturados por **origem e grau de confiabilidade**, mapeando cada tipo de débito para o
  `canonical_cost_key` existente (`iptu`/`debitos`/`condominio`/`itbi`/`registro`/…), **sem dupla
  contagem** (o `canonical_cost_key`/precedência de comissão já trata isso).
- **Totais separados por natureza** (§9), nunca somados entre si:
  1. débitos **confirmados**; 2. débitos **estimados**; 3. despesas **previstas**; 4. valores **não
     apurados**; 5. **exposição consolidada com ressalvas**.
- **Estimativa nunca entra como passivo confirmado** no cálculo definitivo; entra como cenário/ressalva.
  O `preco_maximo` já distingue definitivo×provisório — a Central reforça isso marcando custos
  `DESCONHECIDO`/`ESTIMADO`.
- **Impacto analisado:** custo total de aquisição, investimento necessário, margem de segurança,
  rentabilidade, cenários de saída e parecer do comitê (F8) recebem a exposição **com rótulo de
  confiabilidade**.

---

## 14. Módulo administrativo e telas

**Navegação (Administração):** Visão geral · Municípios e cobertura · Tipos de débito · Fontes de
consulta · Integrações e coletores · Condomínios · Parâmetros financeiros · Parâmetros de estimativa ·
Regras de checklist · Regras de alertas · Parâmetros de risco · Parâmetros de mercado · Parâmetros de
workflow · Histórico de alterações.

**Operações:** consultar, cadastrar, editar, ativar/desativar, definir vigência, validar, ver
histórico, testar configuração (quando aplicável). UI **organizada por módulo** (não uma tela genérica
com dezenas de campos); simples, profissional, preparada para crescer. Lógica de negócio **fora** de
componentes React (serviços/contratos no backend).

**Segurança:** a área administrativa **exige autenticação/RBAC** (hoje inexistente — `FEATURE-
INVENTORY` G9). **Não expor administração sem proteção.** Estratégia: a frente administrativa **depende**
da Onda 11 (auth/RBAC) do `ROADMAP-EXECUTION`; até lá, parametrização fica restrita a um mecanismo
protegido (ex.: token administrativo, como já existe para reveal de credencial) e **não** publicamente
exposta.

---

## 15. Estratégia de versionamento e auditoria de parâmetros

- **Catálogo central** (`parameter`): chave, nome, descrição, categoria, tipo, valor atual, valor
  padrão, unidade, valores permitidos, min/max, abrangência (global/município/tipo/modalidade/
  oportunidade), vigência início/fim, versão, status, responsável, data de atualização.
- **Hierarquia de precedência** (do mais específico ao mais geral): (1) oportunidade, se permitido →
  (2) município → (3) categoria/tipo → (4) global → (5) valor padrão. Alteração global **não**
  sobrescreve silenciosamente um valor específico.
- **Histórico e governança:** toda alteração grava valor anterior/novo, usuário, data/hora,
  justificativa (quando exigida); mantém histórico; identifica a versão vigente em cada análise.
- **Snapshot por execução:** cada análise/consulta grava o **snapshot dos parâmetros usados** (reusa o
  padrão do `token_usage`/`inputs` em `Analysis`/`FinancialAnalysis`). **Alterar um parâmetro hoje não
  muda resultados de análises passadas** — invariante inegociável (preserva V1–V9).

---

## 16. Impactos em banco, backend, frontend e testes

- **Banco:** novas tabelas (`municipality`, `debt_type`, `debt_source`, `property_debt`, `debt_query`,
  `condominium`, `debt_estimate`, `parameter` + histórico). `Debt`/`Cost` preservados; eventual
  `opportunity_id` nullable nas novas (Gate 1). Migrations **aditivas e reversíveis**; **sem backfill**
  sem Gate 2; sem destrutivo. Numeração a partir de `0020` (a próxima livre), coordenada com a Onda 2
  (modalidade também pediu `0020` — sequenciar para evitar colisão; ver §19/decisões).
- **Backend:** novos serviços/contratos/adaptadores (§8); endpoints **aditivos** (Central + Admin);
  `build_finance` passa a receber a exposição estruturada **sem** quebrar o consumo atual de `Debt`.
- **Frontend:** seção de débitos/despesas no dossiê (confirmado/estimado/previsto/não apurado) + área
  administrativa (§14). Lógica fora dos componentes.
- **Testes:** unidade (normalização, estimativa, precedência de parâmetros), integração (adaptadores com
  **fixtures simuladas**, nunca portal real), contrato OpenAPI (adições intencionais), regressão
  (preservação de `Debt`/`Cost`/financeiro/633). Guarda do 633/V1–V9 em toda a suíte.

---

## 17. Dependências com autenticação/RBAC

A frente administrativa é **bloqueada** pela ausência de auth/RBAC. Opções:
- **(A)** Implementar a Central de Débitos (Etapas A–C) **antes** da admin, usando os endpoints de
  parametrização sob **token administrativo** provisório (padrão `PORTAL_ADMIN_TOKEN` já existente),
  sem UI pública.
- **(B)** Priorizar a Onda 11 (auth/RBAC) antes da admin completa.
> Recomendação: **(A)** para não travar a Central; a **UI administrativa completa** só é liberada com
> auth/RBAC (Onda 11). Decisão de negócio em §21.

---

## 18. Riscos técnicos, operacionais e jurídicos

| Risco | Tipo | Mitigação |
|---|---|---|
| Automação de portal violar termos de uso | Jurídico | Validar termos; automação só se permitida; fallback manual |
| Scraping frágil/instável | Técnico | Coletor isolado, versionado, com fixtures; não é 1ª escolha |
| Inventar valor/declarar dívida sem fonte | Jurídico/produto | Determinístico + evidência; LLM só interpreta; `CONFIRMADO≠ESTIMADO` |
| Somar naturezas diferentes | Produto/financeiro | Totais separados (§9); reconciliação por identificador |
| Parâmetro fiscal sem fonte oficial | Jurídico | Bloquear cadastro fiscal sem fonte+vigência (§4/§21) |
| Alterar parâmetro muda análise passada | Dados | Snapshot por execução (§15); V1–V9 intactas |
| Admin exposta sem proteção | Segurança | Depende de auth/RBAC; token provisório até lá (§17) |
| Credencial de portal vazar | Segurança | `secrets_crypto` (Fernet, falha-fechada); nunca em log/tela |
| Colisão de numeração de migration com Onda 2 | Técnico | Sequenciar (§19); confirmar ordem Onda 2 × esta frente |
| LGPD (CPF/CNPJ, dados de ocupante) | Jurídico | Minimizar; base legal; não expor PII indevidamente |

---

## 19. Roadmap dividido em etapas

> Alinhado ao `ROADMAP-EXECUTION.md`. Esta frente é majoritariamente **épico H (custos/parâmetros)** +
> evolução da F4 (fiscal) e transversal (admin). Pode correr **em paralelo** ao caminho crítico do
> workflow, com exceção da UI admin (depende de auth).

**Etapa A — Fundação da Central de Débitos** (migration aditiva; sem integração externa)
- Modelo de domínio (`debt_type`, `property_debt`, `debt_query`), normalização, evidência, histórico.
- **Preserva** `Debt`/`Cost` e endpoints atuais; promove o registro manual existente ao modelo
  normalizado (compatibilidade de leitura).
- **Aceite:** registrar débito normalizado (confirmado/informado) com evidência; `build_finance`
  inalterado no consumo atual; 633/V1–V9 intactos; migrations up/down em banco descartável.

**Etapa B — Municípios e fontes** (cadastro, sem automação ainda)
- `municipality` + cobertura + `debt_source` (classificação §6) para os 4 municípios como **cobertura
  inicial ativa**, cadastrados **via dados** (não lista no código).
- **Aceite:** cobertura independente por município×tipo; nenhuma lista fixa no código; fonte com
  situação + data de validação.

**Etapa C — Condomínio e estimativas**
- Modelo de estimativa + parâmetros + cenários; alertas por idade (parametrizáveis); `condominium`
  preparado (cadastro futuro).
- **Aceite:** estimativa marcada como ESTIMADO (nunca passivo); 3 cenários; idade≠condomínio≠
  financiamento respeitado; alerta de idade respeita qualidade da informação.

**Etapa D — Parametrização administrativa**
- Catálogo `parameter` + precedência + histórico/snapshot + APIs administrativas + telas.
- **Aceite:** alteração com histórico/justificativa; snapshot por execução; análise passada imutável;
  admin protegida (token/RBAC).

**Etapa E — Orquestração e (quando viável) coletores**
- `DebtQueryService` assíncrono + status por consulta; adaptadores por município **conforme viabilidade
  confirmada** (termos + autorização); workers; monitoramento; recuperação de falha.
- **Aceite:** ausência de uma fonte não derruba a apuração; cada consulta tem status próprio; coletor
  testado com fixtures; nenhuma automação sem viabilidade/autorização.

**Etapa F — Consolidação financeira**
- Integração ao dossiê + `build_finance`; totais separados por natureza; impacto na decisão/comitê.
- **Aceite:** 5 totais separados (§9); estimativa não entra como passivo confirmado; exposição com
  rótulo de confiabilidade; sem dupla contagem.

---

## 20. Critérios de aceite (transversais a todas as etapas)
- Preservação: 633/V1–V9/`financial_analyses` V1–V9/`llm_runs` (45 registros)/27 `canonical_key`/
  Central Jurídica intactos; **sem V10**; **sem backfill** sem Gate 2; sem destrutivo; `.env`/segredos
  intocados.
- Migrations aditivas e reversíveis, validadas em banco descartável (upgrade + downgrade).
- Contrato OpenAPI das rotas atuais preservado; adições intencionais documentadas.
- Nenhuma consulta externa paga/real nem scraping sem viabilidade + autorização.
- Determinístico para valores; LLM só interpreta documento com evidência.
- `CONFIRMADO ≠ ESTIMADO ≠ INFORMADO` visível na UI e nos totais.
- Parâmetros de negócio administráveis e versionados; análise passada imutável (snapshot).
- Testes unitários + integração (fixtures) + regressão verdes.

---

## 21. Decisões de negócio pendentes (exigem sua aprovação)
1. **Modelo de dados:** estender `Debt` (opção A) vs nova tabela `property_debt` normalizada (opção B)?
   (Recomendo híbrido: preservar `Debt`/`Cost`, adicionar `property_debt` rico — §10.)
2. **Automação de portais:** autoriza investigar viabilidade/termos de uso de Curitiba/SJP/FRG/Assis?
   A automação só avança por município com viabilidade confirmada; fallback manual permanece.
3. **Parâmetros fiscais (ITBI/emolumentos/ISSQN):** confirmar a regra "nunca cadastrar sem fonte
   oficial + vigência". A Central **introduz** o parâmetro, mas não preenche valor sem fonte.
4. **Água/luz/gás:** confirmar tratamento padrão como **dívida pessoal do ocupante** (não do imóvel),
   salvo base legal/evidência.
5. **Admin × auth/RBAC:** aprova a Central (Etapas A–C) sob token administrativo provisório, deixando a
   **UI admin completa** para depois da Onda 11 (auth)? (§17)
6. **Numeração/sequência de migrations:** esta frente e a Onda 2 (modalidade) disputam `0020` —
   confirmar a ordem de execução (modalidade primeiro? Central primeiro? paralelas com números
   distintos?).
7. **Prioridade vs caminho crítico:** esta frente entra **em paralelo** ao caminho crítico do workflow
   (`ROADMAP-EXECUTION`) ou **antes** de alguma onda?
8. **Cobertura inicial:** confirmar os 4 municípios + quais tipos de débito ativar em cada um na v1
   (ex.: Curitiba IPTU+dívida ativa; demais só IPTU).

---

## 22. Resumo final (critério desta etapa)
- **O que já existe:** `Debt`/`Cost` + CRUD + registro manual de débito municipal + consumo financeiro
  + frente PREFEITURA + evidência/histórico + credenciais seguras. (Preservar tudo.)
- **O que será reaproveitado:** `Debt`/`Cost`, `Evidence`/`EvidenceLink`, `DomainEvent`/`EntityHistory`,
  `secrets_crypto`, padrão `due_diligence_fronts`, `finance.build_finance`, `extraction.py` (para PDF).
- **O que precisa ser desenvolvido:** domínio normalizado de débitos, registries (município/tipo/fonte),
  normalização/reconciliação, estimativa condominial, catálogo de parâmetros + admin, orquestração +
  coletores (quando viável), consolidação financeira por natureza.
- **Hardcodes encontrados:** §3 (classes A–E); nenhum fiscal hardcoded.
- **Parâmetros para a admin:** §4 (mercado, estimativa condominial, alertas de idade, fiscais com
  fonte, operacionais).
- **Consulta oficial por município:** §6 (todos com portal público; API/automação a investigar; sem
  consulta real feita).
- **Onde há automação possível:** Curitiba é o melhor candidato (portal estruturado por inscrição);
  demais a investigar — **sempre** condicionado a termos + autorização.
- **Onde será manual:** todos, na v1 (fallback assistido normalizado).
- **Estimativa condominial:** §11 (parametrizada, 3 cenários, idade≠condomínio≠financiamento, nunca
  passivo confirmado).
- **Integração financeira:** §13 (totais separados por natureza, estimativa como ressalva, sem dupla
  contagem).
- **Decisões que precisam de aprovação:** §21.
- **Roadmap recomendado:** Etapas A→F (§19), em paralelo ao caminho crítico, com UI admin dependente de
  auth/RBAC.

> **Aguardando aprovação explícita do planejamento antes de qualquer implementação.** Nenhum código,
> migration, commit, consulta externa ou scraping será feito sem o seu "ok".

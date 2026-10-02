# EVOLUÇÃO DO BACKLOG — RADAR LEILÃO

**Data:** 02/10/2026  
**Estado de referência:** Task 75.1 integrada; segurança de credenciais corrigida; UI de leiloeiros concluída; validação manual E2E pela UI pendente; Fase 2 ainda não iniciada  
**Escopo:** evolução do Radar Leilão para aprofundar a qualidade da análise de imóveis em leilões extrajudiciais.

---

## 0.1 Pós-TASK 75 (fechamento funcional) — pendências/evolução registradas

A TASK 75 (01/10/2026), complementada pela TASK 75.1 (02/10/2026), tornou os 12 menus navegáveis (hubs globais), adicionou o
domínio Leiloeiros (com credenciais protegidas, migration `0014`), break-even no
Finance Engine e nova identidade visual (ver `PROJECT-STATUS` §23). Ficam como
evolução/Fase 2:

- **E2E de navegador (Playwright)**: não executado nesta rodada (sem ambiente de
  browser automation). Validação de UI permanece manual — é a pendência impeditiva
  do fechamento do MVP visual.
- **Documentos do leiloeiro**: upload binário dedicado (hoje há metadados; o binário
  reutiliza a infra documental de imóveis).
- Cenários financeiros configuráveis e aluguel/yield seguem o engine atual.

---

## 0. Pendências imediatas antes do fechamento do MVP

Estas ações são estabilização/validação do que já existe, não novas funcionalidades de Fase 2.

1. **E2E financeiro pela UI (P1):** validar preenchimento, gravação, recarga e apresentação do preço máximo definitivo/provisório.
2. **Premissas incompletas (P1):** confirmar que ITBI, registro, comissão de arrematação, corretagem e tributo ausentes aparecem como pendências e que a estimativa não é tratada como limite confiável de lance.
3. **Regressão da aplicação (P1):** executar health check e os fluxos principais após atualizar a cópia local; registrar logs e defeitos reproduzíveis.
4. **DataJud real (P2):** os testes gated/skipped não comprovam uma consulta real; validar somente quando houver configuração e condições de acesso.
5. **Documentação:** manter README, PROJECT-STATUS, SPEC e IMPLEMENTATION-REFERENCE alinhados ao commit mais recente. A atualização documental deve refletir o commit mais recente e manter histórico anterior intacto.

**Critério para fechar:** evidência registrada de UI real, premissas persistidas após recarga, estado provisório/definitivo correto e nenhuma regressão bloqueante. Até então, o status permanece “validação pendente”.

## 1. Objetivo deste documento

Este documento organiza a evolução do produto após o fechamento do MVP.

A premissa principal é:

> **A análise do imóvel é o produto central do Radar Leilão.**

O MVP já possui o motor central necessário para executar essa análise: processamento documental, RAG, cinco agentes LLM, evidências, Checklist Mestre, Risk Engine, Verdict Engine, histórico e memória.

A Fase 2, portanto, **não começa construindo a análise do zero**. Ela deve aprofundar a qualidade da análise e aumentar a capacidade do sistema de correlacionar evidências entre os diferentes domínios.

---

## 2. Ordem conceitual de evolução

A evolução deve priorizar a qualidade da decisão de investimento, nesta ordem:

1. **Jurídico**
2. **Financeiro**
3. **Mercado**
4. **Ocupação / desocupação**
5. **Correlação multidomínio e qualidade das evidências**
6. **Novas fontes externas, automações e MCP como meios de ampliar os dados**

MCP, APIs e automações não são o objetivo final. São mecanismos para alimentar e enriquecer os pilares de análise.

---

## 3. Pilar 1 — Análise Jurídica

A análise jurídica deve deixar de depender somente da interpretação do agente Jurídico sobre edital e matrícula e evoluir para uma diligência jurídica estruturada.

### Escopo principal

- Matrícula completa e histórico de averbações.
- Proprietário e cadeia dominial quando disponível.
- Alienação fiduciária.
- Hipoteca.
- Penhora.
- Indisponibilidade.
- Usufruto.
- Arresto.
- Gravames e restrições.
- Cancelamentos e averbações relevantes.
- Inconsistências entre matrícula e edital.
- Regras e obrigações do edital.
- Responsabilidade por condomínio, IPTU e demais débitos.
- Comissão do leiloeiro.
- Forma e prazo de pagamento.
- Regras de financiamento.
- Posse e ocupação.
- Processos judiciais relacionados ao imóvel ou às partes, quando identificáveis.
- Classificação do impacto jurídico.
- Evidência obrigatória para cada conclusão.
- Identificação explícita do que está confirmado, não identificado ou pendente.

### Resultado esperado

O sistema deve conseguir responder, de forma rastreável:

> **"Existe algum impedimento ou risco jurídico relevante para adquirir este imóvel? Qual é a evidência, qual é o impacto e o que precisa ser diligenciado antes do lance?"**

---

## 4. Pilar 2 — Análise Financeira

A análise financeira deve transformar o preço do leilão em **custo real de aquisição e investimento**.

### Escopo principal

- Preço de aquisição.
- Comissão do leiloeiro.
- ITBI.
- Registro.
- Escritura, quando aplicável.
- Condomínio.
- IPTU.
- Débitos e contingências.
- Reforma.
- Custos de desocupação.
- Custos de manutenção.
- Custo de capital.
- Cenário de venda.
- Cenário de aluguel.
- Cenário de manutenção/hold.
- Yield.
- Margem de segurança.
- Break-even.
- Preço máximo de compra.

### Evolução importante

A fórmula de preço máximo deve ser **explicitamente definida, versionada e explicável**, evitando que o sistema invente uma fórmula quando a regra canônica não estiver definida.

---

## 5. Pilar 3 — Análise de Mercado

O agente Mercado já existe no MVP. A evolução é aumentar a qualidade e a objetividade dos dados utilizados.

### Escopo principal

- Comparáveis reais de venda.
- Comparáveis reais de aluguel.
- Preço por m².
- Área comparável correta.
- Distância geográfica.
- Similaridade do imóvel.
- Condomínio/empreendimento.
- Bairro e microrregião.
- Oferta concorrente.
- Liquidez.
- Histórico de preços quando disponível.
- Faixa conservadora/base/otimista.
- Desconto necessário para saída.
- Estratégia de venda ou aluguel.

### Resultado esperado

O sistema deve deixar de responder apenas:

> "O preço parece atrativo."

E evoluir para:

> "Considerando comparáveis válidos, localização, liquidez, custos e estratégia de saída, qual faixa de valor é suportada pelos dados e qual desconto é necessário para compensar os riscos?"

---

## 6. Pilar 4 — Ocupação e Desocupação

Ocupação não deve ser tratada apenas como um campo documental. Ela possui impacto jurídico, financeiro e operacional.

### Escopo principal

- Imóvel ocupado ou desocupado.
- Tipo provável de ocupante.
- Existência de locação.
- Contrato registrado ou não.
- Relação entre ocupação e edital.
- Estratégia de desocupação.
- Prazo estimado.
- Custo estimado.
- Risco jurídico.
- Impacto sobre liquidez.
- Impacto sobre preço máximo.

A desocupação deve alimentar o cálculo financeiro e o Risk Engine.

---

## 7. Pilar 5 — Correlação multidomínio

A evolução mais importante do produto é deixar de tratar os agentes como análises independentes.

Exemplo:

**Matrícula**
→ identifica gravame  
→ Jurídico classifica impacto  
→ Financeiro estima custo/contingência  
→ Mercado avalia impacto na liquidez  
→ Ocupação avalia prazo/custo  
→ Risk Engine consolida  
→ preço máximo é ajustado  
→ Verdict Engine produz a conclusão.

O objetivo é uma análise **multidomínio**, na qual uma evidência relevante em um domínio possa alterar os demais quando houver relação causal ou regra determinística.

---

## 8. Pilar 6 — Fontes externas, APIs, automações e MCP

Esses componentes devem entrar como **enablers da análise**, não como prioridade isolada.

Possíveis fontes:

- APIs jurídicas.
- DataJud e fontes processuais públicas.
- Bases de mercado.
- Dados imobiliários públicos.
- Dados de localização.
- Dados de aluguel.
- Dados históricos.
- APIs da Caixa e outros bancos, quando disponíveis.
- Automação de coleta.
- MCP para ferramentas externas.

A arquitetura deve preservar:

- fonte;
- data/hora da consulta;
- parâmetros;
- resposta original quando permitido;
- normalização;
- evidência;
- confiança;
- versionamento.

---

# 9. Backlog proposto

## Fase 2A — Jurídico

**Objetivo:** transformar o Jurídico em um módulo de diligência estruturada e rastreável.

### JUR-01 — Fundação e contrato jurídico

- Definir contrato unificado do módulo.
- Definir modelos de domínio.
- Definir configuração de fontes.
- Definir catálogo de endpoints.
- Definir credenciais/API keys.
- Definir persistência e histórico de consultas.
- Definir normalização de respostas.
- Testes de contrato.

**Saída:** módulo jurídico com fundação estável, ainda sem depender de uma fonte específica.

### JUR-02 — Integração DataJud e adapters

- Implementar provider/adapters.
- Catálogo nacional parametrizado.
- Consultas paralelas.
- Busca por identificadores disponíveis.
- Normalização de processos, partes, assuntos e movimentos.
- Tratamento de indisponibilidade e diferenças entre endpoints.
- Evidência de origem.

**Saída:** pesquisa jurídica nacional baseada em DataJud, dentro dos limites da fonte.

### JUR-03 — Persistência, histórico e confiabilidade

- Persistir consultas.
- Persistir fontes e respostas normalizadas.
- Histórico de sincronização.
- Deduplicação.
- Idempotência.
- Retry/backoff.
- Timeout.
- Rate limit.
- Registro de erros.
- Observabilidade básica.

**Saída:** módulo confiável para consultas repetidas e reprocessamento.

### JUR-04 — Correlação com o imóvel e análise jurídica

- Relacionar resultados processuais ao imóvel.
- Relacionar resultados às partes quando houver identificadores.
- Classificar impacto processual.
- Correlacionar processo + matrícula + edital.
- Gerar evidências jurídicas rastreáveis.
- Classificar risco jurídico.
- Identificar pendências e diligências necessárias.
- Integrar o resultado ao Checklist/Risk Engine/Verdict.

**Saída:** o dado jurídico passa a impactar efetivamente a análise do imóvel.

### JUR-05 — Integração Radar + testes E2E

- Integrar o módulo ao fluxo do Radar.
- Reanálise quando nova informação jurídica alterar o risco.
- Testes unitários.
- Testes de contrato.
- Testes de integração.
- Teste E2E com imóvel real.
- Documentação operacional.
- Hardening das fontes.

**Saída:** módulo jurídico operacional dentro do Radar, com rastreabilidade ponta a ponta.

---

## Fase 2B — Financeiro

1. Definição formal do custo econômico total.
2. Fórmula canônica de preço máximo.
3. Cenários venda/aluguel/hold.
4. Custos de desocupação e contingências.
5. Sensibilidade e margem de segurança.
6. Integração com Risk Engine e Verdict.

---

## Fase 2C — Mercado

1. Coleta de comparáveis reais.
2. Normalização dos comparáveis.
3. Seleção por similaridade e localização.
4. Preço/m² e aluguel/m².
5. Liquidez e oferta.
6. Cenários conservador/base/otimista.
7. Valuation integrado ao preço máximo.

---

## Fase 2D — Ocupação / Desocupação

1. Classificação da ocupação.
2. Identificação de evidências.
3. Estratégias de desocupação.
4. Estimativa de prazo/custo.
5. Impacto jurídico e financeiro.
6. Integração ao risco e ao preço máximo.

---

## Fase 2E — Correlação e decisão

1. Correlação entre Jurídico + Financeiro + Mercado + Ocupação.
2. Propagação de eventos entre domínios.
3. Reanálise incremental mais inteligente.
4. Explicabilidade multidomínio.
5. Evals com conjunto maior de imóveis reais.
6. Calibração de risco e qualidade das evidências.

---

## Fase 2F — Fontes e automação

1. APIs externas.
2. DataJud e demais fontes jurídicas.
3. Fontes de mercado.
4. Automações/RPA quando necessário.
5. MCP.
6. Novas fontes de dados.
7. Automação do pipeline de coleta.

---

# 10. Regra de priorização

Uma nova tecnologia ou integração só deve entrar no backlog quando responder a uma necessidade concreta da análise.

A pergunta de priorização é:

> **"Essa capacidade melhora a qualidade da análise, reduz uma incerteza relevante ou reduz trabalho manual de diligência?"**

Se não, permanece secundária.

---

# 11. Estratégia de implementação com Kiro

Para preservar qualidade e controlar consumo de tokens:

- uma TASK por vez;
- cada TASK deve ter escopo fechado;
- Kiro implementa;
- commit obrigatório;
- auditoria do commit;
- testes;
- somente depois inicia a próxima TASK.

O módulo Jurídico, apesar da especificação original ser extensa, pode ser executado em **5 tasks principais (JUR-01 a JUR-05)** sem perder o desenho arquitetural. Cada task pode conter subtarefas internas, mas o Kiro recebe uma unidade de entrega clara por vez.

---

# 12. Critério de conclusão da evolução jurídica

O módulo Jurídico só deve ser considerado concluído quando:

- fontes configuradas funcionarem;
- consultas forem rastreáveis;
- respostas forem normalizadas;
- histórico for preservado;
- erros forem tratados;
- processos puderem ser correlacionados ao imóvel quando houver evidência suficiente;
- impacto jurídico for classificado;
- evidências forem apresentadas ao usuário;
- Checklist/Risk/Verdict receberem o impacto jurídico;
- reanálise funcionar quando uma nova informação alterar o caso;
- houver teste E2E com imóvel real.

---

## 13. Relação com a documentação existente

- `SPEC-VIBE-CODING-RADAR-LEILAO.md` → visão de negócio e arquitetura do Radar.
- `IMPLEMENTATION-REFERENCE.md` → implementação efetivamente existente.
- `PROJECT-STATUS.md` → estado atual do projeto.
- `PROJECT-HISTORY.md` → histórico de decisões e implementações.
- `EVOLUTION-BACKLOG.md` → evolução pós-MVP e priorização do backlog.
- Spec específica do módulo Jurídico → requisitos detalhados da implementação jurídica.

**Regra:** a spec específica continua sendo a fonte detalhada dos requisitos do módulo; este documento define a sequência executiva e a divisão em tasks.

---

# 14. Evoluções derivadas da Task 75.1 (segurança de credenciais)

Entregue na Task 75.1: credenciais de portal cifradas (Fernet/AES, chave de ambiente)
e endpoint de recuperação protegido por token de operação (`X-Portal-Admin-Token`),
com falha fechada. Ficam como evolução pós-MVP:

1. **Autenticação/autorização por usuário**: hoje a recuperação da credencial usa um
   token de operação único, não um controle por usuário/perfil (o projeto não tem
   camada de autenticação de usuários). Evoluir para login + perfis + trilha de
   auditoria por identidade quando houver múltiplos operadores.
2. **Rotação de chave (`PORTAL_SECRET_KEY`)**: suportar múltiplas chaves/versões
   (o prefixo `enc:v1:` já reserva espaço para versionamento) e re-cifragem em lote.
3. **Cofre de segredos gerenciado**: quando sair do MVP local, considerar um KMS/secret
   manager externo em vez de chave em `.env` (fora do escopo atual por decisão da task).
4. **Upload binário de documentos do leiloeiro**: hoje são metadados; reutilizar a infra
   documental de imóveis para anexos binários dedicados do leiloeiro.

---

# 15. Evoluções derivadas da Task 75.2 (CRUD cadastral padronizado)

Entregue na 75.2: edição/exclusão de dados cadastrais com histórico (before/after) +
evento, comissão de arrematação canônica (precedência Auction>Cost, sem dupla
contagem), movimentação processual append-only, e histórico de leiloeiro/portal sem
exposição de segredo. Ficam como evolução pós-MVP:

1. **DELETE de imóvel/leilão com inativação (soft delete)**: hoje imóvel e leilão só
   têm edição (sem DELETE) para preservar análises/vereditos associados. Avaliar
   inativação por status + arquivamento, mantendo o histórico.
2. **Reanálise incremental automática a partir do evento cadastral**: hoje a edição
   emite o `DomainEvent` mas a reanálise é disparada manualmente (`/reanalisar`).
   Avaliar enfileiramento/opt-in para reanálise guiada por impacto.
3. **Edição assistida de movimentações processuais**: correção de erro de digitação
   em andamento é append-only (novo registro) por decisão de auditoria; avaliar uma
   correção explícita rastreada (supersede) se houver demanda operacional.
4. **Normalização de categorias de custo na UI**: o mapa canônico vive no backend;
   avaliar um seletor de categoria sugerida no formulário de custo para reduzir
   divergência de texto livre.

# RADAR LEILÃO — ROADMAP MASTER DO PRODUTO

**Versão:** 1.0  
**Data de consolidação:** 07/11/2026  
**Branch de referência:** `main`  
**Baseline documental:** `52a3eb9cdb9fb478c7374275c83405c64b7d0a9f`  
**Natureza:** visão-alvo do produto e plano mestre de evolução. Este documento não afirma que funcionalidades planejadas já estejam implementadas.

---

## 1. Visão do produto

O Radar Leilão será uma plataforma de inteligência e operação de investimentos imobiliários em leilões no Brasil. Deve conduzir uma oportunidade desde sua descoberta até sua decisão, aquisição, regularização e rentabilização, ou seu descarte fundamentado.

O produto deverá permitir:
- descobrir oportunidades em fontes configuradas;
- identificar imóvel, oferta, modalidade, regras e prazos;
- organizar documentos e evidências;
- executar análises documental, jurídica, financeira, física, mercadológica e operacional;
- aplicar checklists e regras adequados à modalidade;
- calcular viabilidade, custo total, cenários e lance máximo;
- recomendar e registrar decisões com justificativas e aprovações;
- controlar participação, arrematação, pagamentos, transferência, posse e regularização;
- acompanhar reforma, locação, venda, receitas, despesas e resultado realizado;
- manter trilha auditável de dados, evidências, versões, decisões e ações.

**Princípio:** o sistema apoia a decisão; não substitui advogado, leiloeiro, cartório, autoridade pública, avaliação técnica ou validação humana exigida por lei ou pelo risco.

## 2. Definição de 100%

O produto só poderá ser declarado 100% quando:
1. Todos os domínios obrigatórios estiverem implementados e integrados.
2. Os fluxos principais puderem ser executados de ponta a ponta para as modalidades e fontes declaradas como suportadas.
3. Cada etapa tiver critérios de entrada, saída, bloqueios, evidências e responsável.
4. Os cálculos críticos forem determinísticos, versionados, reproduzíveis e testados.
5. As conclusões jurídicas forem fundamentadas em fontes identificáveis, com data, vigência, jurisdição e validação apropriada.
6. O isolamento entre imóveis e oportunidades estiver garantido.
7. O histórico for auditável e decisões anteriores não forem apagadas.
8. Segurança, permissões, backups, observabilidade, recuperação e operação estiverem validados.
9. Testes unitários, integração, contrato, E2E e regressão estiverem verdes.
10. Documentação, runbooks, limitações conhecidas e critérios de suporte estiverem atualizados.

100% significa conclusão do escopo explicitamente suportado, não integração com todos os portais ou automatização impossível/ilegal. Cada fonte e modalidade deve ter status de suporte explícito.

## 3. Jornada funcional F0–F13

| Fase | Nome | Resultado esperado |
|---|---|---|
| F0 | Radar e descoberta | Oportunidade identificada, origem e data de captura rastreáveis |
| F1 | Classificação/modalidade | Modalidade, regras aplicáveis, jurisdição e cronograma identificados |
| F2 | Cadastro e estruturação | Property e Opportunity corretamente separados e vinculados |
| F3 | Análise documental | Documentos versionados, extraídos e evidências rastreáveis |
| F4 | Análise jurídica | Riscos, fundamentos, fontes e validações registrados |
| F5 | Due diligence | Checklist aplicável executado, pendências e responsáveis identificados |
| F6 | Análise financeira | Custo total, cenários, rentabilidade e lance máximo reproduzíveis |
| F7 | Mercado e valuation | Valor de referência, comparáveis, liquidez e incerteza apresentados |
| F8 | Comitê de decisão | Aprovação/reprovação/pendência justificada; hard stops respeitados |
| F9 | Estratégia de aquisição | Plano de participação e limite de lance aprovado |
| F10 | Arrematação e pagamento | Resultado, obrigações, prazos e comprovantes controlados |
| F11 | Transferência e posse | Registro, transferência e posse acompanhados conforme modalidade |
| F12 | Regularização e preparação | Pendências, obras, orçamento e preparação controlados |
| F13 | Rentabilização e encerramento | Locação/venda/holding, resultado realizado e encerramento registrados |

Fluxos alternativos obrigatórios:
- oportunidade descartada em qualquer fase, com motivo e evidência;
- leilão suspenso, cancelado, adiado ou sem lance;
- lance não vencedor;
- arrematação frustrada ou desfeita;
- impedimento jurídico confirmado;
- oportunidade reaberta após novo edital, matrícula, preço ou fato relevante;
- aquisição concluída com imóvel mantido em carteira, alugado ou vendido.

## 4. Domínios e capacidades transversais

### 4.1 Descoberta e ingestão
Fontes configuráveis, conectores autorizados, importação manual/arquivo/API, agendamento, deduplicação, atualização incremental, monitoramento de falhas, proveniência e política de uso. Não presumir scraping permitido nem contornar autenticação, CAPTCHA ou controles de acesso.

### 4.2 Imóvel e oportunidade
`Property` representa o bem físico/jurídico. `Opportunity` representa uma oferta/processo de aquisição específico. Um imóvel pode ter várias oportunidades ao longo do tempo. Edital, preço, modalidade, cronograma, participantes, análises, decisões e workflow devem pertencer à oportunidade quando variarem por oferta. Documentos gerais do imóvel podem continuar no nível Property; documentos específicos de uma oferta precisam ter associação explícita sem misturar contextos.

### 4.3 Documentos, OCR e evidências
Upload, origem, hash, versão, tipo, páginas, OCR, extração estruturada, trechos, confiança, vínculo com imóvel/oportunidade, revisão humana e cadeia de evidências. Nunca inventar página, trecho, conteúdo ou metadado ausente.

### 4.4 Inteligência jurídica
Central Jurídica versionada; legislação oficial, atos normativos, jurisprudência e regras práticas separados; vigência temporal, jurisdição, fonte, URL, data de consulta e status de verificação. Regras devem ser parametrizadas e revisadas. LLM pode extrair/sugerir hipóteses, nunca declarar sozinho impedimento jurídico definitivo.

### 4.5 Due diligence e checklists
Checklists dinâmicos por modalidade, jurisdição, tipo de imóvel, ocupação e circunstâncias. Preservar os 27 `canonical_key` atuais; extensões devem ser versionadas e migráveis sem renomear/excluir chaves históricas. Cada item terá aplicabilidade, evidência, estado, responsável, prazo, motivo de dispensa e trilha.

### 4.6 Financeiro e valuation
Motor determinístico com parâmetros versionados por jurisdição e vigência. Custos de aquisição, comissão, tributos, débitos, condomínio, IPTU, cartório, honorários, desocupação, reforma, carregamento, financiamento, venda/locação e impostos. Apresentar cenários, sensibilidade, fluxo de caixa, ROI, margem, TIR, yield, payback, custo total e preço máximo de lance. Valores estimados devem ser diferenciados de valores confirmados.

### 4.7 Risco, decisão e workflow
Workflow determinístico F0–F13, transições permitidas, gates, responsáveis, prazos, bloqueios, reabertura e histórico append-only. Score não substitui hard stop. Apenas impedimento CONFIRMADO, com evidência suficiente e validação adequada, bloqueia decisão conforme regra configurada.

### 4.8 Aquisição e pós-arrematação
Calendário, regras do certame, plano de lance, limite aprovado, resultado, pagamentos, comissão, parcelas, multas, documentos, registro, posse, desocupação, regularização, obras e fornecedores. O sistema controla tarefas e evidências; não simula protocolo/registro real sem integração autorizada.

### 4.9 Rentabilização
Estratégia de manter, alugar ou vender; preparação, anúncio, contratos, receitas, despesas, vacância, manutenção, impostos, preço de venda e resultado realizado. Fechamento deve reconciliar projeção versus realizado.

### 4.10 Plataforma e governança
Autenticação, autorização/RBAC, segregação de dados, auditoria, logs, observabilidade, filas/jobs quando necessários, gestão de segredos, backup/restore testado, segurança de upload, rate limiting, política de retenção, CI/CD e documentação operacional.

## 5. Roadmap de execução em poucos ciclos

A implementação será organizada em **3 grandes ciclos de trabalho do Kiro**, cada um com entregas internas, commits pequenos e gates de validação. Não significa três commits nem desenvolvimento monolítico.

### Ciclo 1 — Auditoria e preparação
- Auditar código, banco, migrations, rotas, frontend, testes e integrações.
- Confrontar funcionalidades existentes com este roadmap.
- Produzir matriz real de status: NÃO INICIADO / ESPECIFICADO / EM DESENVOLVIMENTO / IMPLEMENTADO / VALIDADO / CONCLUÍDO.
- Registrar evidências, lacunas, riscos, dependências e estimativa relativa.
- Resolver divergências documentais sem apagar histórico.
- Confirmar baseline de dados e testes antes de código.
**Saída:** backlog fechado e plano de execução baseado no repositório real.

### Ciclo 2 — Construção integrada da plataforma
Executar em ondas internas:
1. Fundação: M0 modularização gradual + B1 Opportunity/Workflow.
2. Domínio de oportunidade, modalidade e isolamento.
3. Documentos/evidências e inteligência jurídica.
4. Checklists e due diligence dinâmica.
5. Motor financeiro e valuation.
6. Hard stops, comitê e decisão.
7. Estratégia, aquisição, pagamentos e obrigações.
8. Registro, posse, regularização e preparação.
9. Locação, venda e encerramento.
10. Radar, conectores, dashboards e automações operacionais.
11. Segurança, RBAC, auditoria, observabilidade e operação.
**Regra:** respeitar dependências; uma etapa só avança após critérios de aceite. Paralelismo apenas quando arquivos/domínios forem independentes.

### Ciclo 3 — Validação e fechamento
- Testes de regressão e compatibilidade.
- E2E de cada modalidade/fonte suportada, incluindo fluxos alternativos.
- Testes de isolamento, concorrência, idempotência e integridade histórica.
- Validação financeira por casos conhecidos e revisão de fórmulas.
- Revisão jurídica e de proveniência.
- Segurança, backup/restore, observabilidade e runbooks.
- Correção de gaps, documentação e release checklist.
**Saída:** relatório de aceite 100%, limitações residuais explícitas e versão candidata.

## 6. Regras de execução
- Preferir poucas instruções abrangentes ao Kiro; dividir por ciclos e gates, não por microtarefas conversacionais.
- Kiro pode decompor internamente em tarefas/PRs/commits, mas deve manter um plano mestre.
- Não implementar tudo em um único diff. Entregas pequenas, coerentes e reversíveis.
- Não alterar contrato existente sem justificativa, versionamento e teste de compatibilidade.
- Nenhum dado real é descartado para facilitar migração.
- Migrations aditivas, upgrade/downgrade testados em banco descartável.
- Sem chamadas pagas, scraping amplo ou integração externa real sem autorização.
- Nenhum LLM automático em GET, CRUD ou workflow determinístico.
- Toda saída de IA deve registrar modelo, versão, prompt/template, fontes, timestamp, custo quando disponível e estado de validação.
- Toda conclusão deve distinguir FATO DOCUMENTAL, DADO DE FONTE, INFERÊNCIA, HIPÓTESE, ESTIMATIVA e ORIENTAÇÃO.
- Toda decisão relevante deve ser explicável e auditável.

## 7. Decisões de arquitetura já aprovadas
- `Property` e `Opportunity` são entidades distintas.
- Uma Property pode ter N Opportunities.
- `opportunity_id` nullable nas nove tabelas definidas em `MATRIZ-OPPORTUNITY-ID.md`, com NULL representando legado durante a transição.
- `post_auctions`: manter `property_id UNIQUE` nesta etapa.
- `costs` e `debts`: adiar `opportunity_id` para o épico financeiro.
- Documentos continuam vinculados ao imóvel nesta etapa; associação específica à oferta será evoluída com modelagem explícita, sem misturar contextos.
- Backfill 0021 não autorizado; exige autorização adicional e pg_dump.
- `WorkflowTransition` append-only; decisões antigas não são apagadas.
- LLM pode sinalizar hipótese, não confirmar sozinho hard stop.
- Hard stop só bloqueia quando CONFIRMADO e validado segundo regra.
- Workflow orquestra e consulta domínios; não recalcula análises nem dispara LLM.

## 8. Preservação obrigatória
Até autorização explícita e plano de migração:
- property 633 — COND PARQUE ARVOREDO RESIDENCIAL CLUBE;
- análises V1–V9 e análises financeiras V1–V9;
- histórico de `llm_runs`;
- 27 `canonical_key` do Checklist Mestre;
- Central Jurídica e conteúdo curado;
- documentos, versões, evidências, riscos, vereditos e histórico.
Proibido: reset, truncate, drop de dados, seed destrutivo, `docker compose down -v`, remoção de volumes, backfill 0021 sem Gate 2, LLM real ou chamadas pagas sem autorização.

## 9. Governança de status
Usar os estados:
- `NAO_INICIADO`: não há implementação nem especificação suficiente.
- `ESPECIFICADO`: escopo/arquitetura documentados, sem implementação funcional.
- `EM_DESENVOLVIMENTO`: implementação em andamento.
- `IMPLEMENTADO`: código existe, mas ainda não passou validação completa.
- `VALIDADO`: critérios técnicos/funcionais passaram com evidências.
- `CONCLUIDO`: integrado, documentado, operacional no escopo suportado e aceito.

Percentual deve ser calculado por critérios ponderados e evidências, não por impressão ou número de arquivos. Separar progresso de especificação, implementação e validação.

## 10. Documentos relacionados
- `PRODUCT-SCOPE-100.md`
- `ACCEPTANCE-CRITERIA-MASTER.md`
- `PROJECT-STATUS.md`
- `PROJECT-HISTORY.md`
- `TODO-PLATAFORMA-COMPLETA.md`
- `TODO-WORKFLOW-FOUNDATION.md`
- `SEQUENCING-M0-B1.md`
- `MATRIZ-OPPORTUNITY-ID.md`
- `SPEC-OPPORTUNITY-ISOLATION.md`
- `SPEC-INVALIDATION-STRATEGY.md`
- `SPEC-HARD-STOPS.md`

---
**Regra final:** este roadmap é a visão-alvo. O status de cada item deve ser confirmado por inspeção de código, testes e execução; texto de planejamento não é evidência de implementação.

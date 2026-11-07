# TODO — Plataforma completa Radar Leilão

Backlog planejado, não declaração de funcionalidades implementadas. Ver docs/PROMPT-KIRO-PLATAFORMA-COMPLETA.md.

## P0 — Diagnóstico, integridade e segurança
- [ ] Diagnóstico de módulos, tabelas, endpoints, migrations, engines e testes.
- [ ] Matriz capacidade atual × gap × reuso × implementação × testes.
- [ ] Separar judicial, extrajudicial/alienação fiduciária, outras garantias e venda direta.
- [ ] Estados explícitos de incerteza; ausência de resultado não é ausência de risco.
- [ ] Matriz de evidências com fonte, data, validade, abrangência, página/trecho, hash, confiança e limitações.
- [ ] Hard stops que score não possa mascarar.
- [ ] Preservar 27 canonical_key, imóvel 633, V1–V9 e baseline conhecida de 45 llm_runs.
- [ ] GET/CRUD/navegação não criam análise LLM, versão ou custo externo.
- [ ] Segurança, RBAC, LGPD, segredos, auditoria, retenção e proteção documental.

## P0 — Central Jurídica
- [ ] Conferir fonte primária, redação vigente/histórica e alterações.
- [ ] Separar verificação da fonte, vigência, transcrição, interpretação e aplicação.
- [ ] Aplicabilidade por modalidade, etapa, jurisdição e fatos.
- [ ] Revisar Lei 9.514/97 arts. 26, 27 e 37-A, alterações e transições.
- [ ] CPC/arrematação judicial separado do extrajudicial.
- [ ] Revisar CTN 130/131 e condomínio em trilhas próprias.
- [ ] Revisar locação, preferência, denúncia, averbação, usufruto e direitos reais.
- [ ] Jurisprudência somente com número, órgão, tese, data, situação e fonte oficial.
- [ ] Recuperar “136 + 27 → 45 regras”; não fabricar conteúdo.
- [ ] Auditar cobertura dos 27 canonical_key.
- [ ] Registrar revisor, data, próxima revisão e histórico de alterações.

## P1 — Workflow
- [ ] F0 intake, origem, snapshot, deduplicação e qualidade.
- [ ] F1 triagem/classificação inequívoca.
- [ ] F2 cofre documental versionado e OCR com página/trecho.
- [ ] F3 análise jurídica registral, edital, intimação, consolidação e processos.
- [ ] F4 diligência fiscal, condominial, serviços, certidões e urbanismo.
- [ ] F5 inspeção física, localização, entorno e limitações.
- [ ] F6 ocupação, locação, posse, negociação voluntária e estratégia judicial.
- [ ] F7 motor financeiro completo, cenários, preço máximo, fluxo e sensibilidade.
- [ ] F8 comitê, hard stops e aprovação humana.
- [ ] F9 calendário, lance, pagamento, comissão e resultado.
- [ ] F10 transferência, título, ITBI, registro e matrícula atualizada.
- [ ] F11 posse, regularização e reforma.
- [ ] F12 venda/locação/holding e resultado realizado.
- [ ] F13 encerramento, dossiê e retrospectiva.

## P1 — Checklists
- [ ] Preservar 27 canonical_key.
- [ ] Checklist por modalidade, fase, tipo, jurisdição, ocupação, finalidade e risco.
- [ ] Cada item com pergunta verificável, finalidade, evidência, critério, fonte, criticidade, responsável e validade.
- [ ] Estados: NAO_INICIADO, PENDENTE_DOCUMENTO, EM_VALIDACAO, CONFIRMADO, NAO_CONFIRMADO, NAO_APLICAVEL_JUSTIFICADO, DIVERGENTE, VENCIDO, BLOQUEADO, REVISAR.
- [ ] “Não encontrado” exige escopo de consulta; NAO_APLICAVEL exige justificativa.
- [ ] Auditoria de cobertura, duplicidade, conflito e itens vagos.

## P1 — Custos/tributos
- [ ] Parametrizar por jurisdição, ato, base, vigência e fonte oficial.
- [ ] Validar ITBI, registro, escritura, emolumentos, FUNREJUS, fundos e selos.
- [ ] Validar IPTU, condomínio, consumo, custas, honorários, mudança, reforma, carregamento e saída.
- [ ] IRPF/IRPJ e ganho de capital conforme regime e requisitos.
- [ ] Validar regra dos 180 dias e redutores sem generalização.
- [ ] Evitar dupla contagem Auction/Costs/Debts/Pós.
- [ ] Memória de cálculo, fonte, data-base e incerteza.

## P1 — Ocupação/posse
- [ ] Classificar ocupante e fundamento sem inferência sensível desnecessária.
- [ ] Mapear propriedade, posse, locação, usufruto, comodato e direitos.
- [ ] Negociação voluntária documentada, aprovada e condicionada.
- [ ] Minutas respeitosas revisadas por advogado; sem ameaça/coerção.
- [ ] Simulador taxa ocupação após validar incidência, base, período e legitimidade.
- [ ] Workflow de advogado/processo/custas/prazos estimados sem prometer liminar.
- [ ] Bloquear autotutela, corte de serviços, entrada forçada e retirada de bens.

## P2 — Integrações/IA/UX
- [ ] Validar portais/serviços anotados, termos, API, autorização, custo e cobertura.
- [ ] Fontes oficiais autorizadas para registro, prefeitura, tribunais, certidões e mapas.
- [ ] RAG com documentos versionados e citações por página/trecho.
- [ ] Limites de custo por imóvel/fase/documento e controle de execução.
- [ ] Dashboard, próximos passos, dossiê, explicação das recomendações e relatórios.
- [ ] Indicadores projetado × realizado, descarte, ROI, tempo de posse e desvios.
- [ ] Revisão periódica de regras, checklists, fontes e parâmetros.

## P0 — Testes e preservação
- [ ] Unitários, PostgreSQL integração, API, frontend e E2E quando disponível.
- [ ] Migrations upgrade/downgrade e rollback.
- [ ] Fixtures judicial/extrajudicial e casos incompletos/divergentes/homônimos.
- [ ] Não regressão canonical_key e histórico.
- [ ] GET/CRUD não executa LLM.
- [ ] Nunca declarar E2E sem evidência.
- [ ] Nenhum reset ou alteração do imóvel 633 sem autorização.


---

## ROADMAP MASTER — backlog consolidado de produto (07/11/2026)

**Referências obrigatórias:** `ROADMAP-MASTER.md`, `PRODUCT-SCOPE-100.md`, `ACCEPTANCE-CRITERIA-MASTER.md`. Este bloco complementa o backlog anterior; não marca itens como implementados sem auditoria.

### CICLO 1 — Auditoria e preparação
- [ ] Inventariar backend: módulos, serviços, modelos, rotas, jobs, integrações e dependências.
- [ ] Inventariar frontend: páginas, hubs, componentes, fluxos e estados de UX.
- [ ] Inventariar banco: tabelas, relacionamentos, migrations e integridade.
- [ ] Inventariar testes: unitários, integração, contrato, E2E, segurança e cobertura dos fluxos críticos.
- [ ] Mapear fontes de dados e status de autorização/credenciais.
- [ ] Mapear cada requisito F0–F13 para código, teste e evidência.
- [ ] Atribuir status oficial por capacidade: NÃO_INICIADO / ESPECIFICADO / EM_DESENVOLVIMENTO / IMPLEMENTADO / VALIDADO / CONCLUIDO / BLOQUEADO.
- [ ] Registrar baseline de rotas/OpenAPI, testes, migrations e dados críticos.
- [ ] Consolidar dependências, riscos, lacunas, sequência e estimativa relativa.
- [ ] Atualizar este backlog, PROJECT-STATUS e PROJECT-HISTORY com evidências.

### CICLO 2 — Construção integrada (ondas internas)
- [x] **Onda 0 — Fundação M0: modularização gradual da API, preservando contrato** — concluída
  20/09/2026 (HEAD `1d2d06d`). Baseline OpenAPI (99 paths) + guard-rail de contrato; fix da
  migration de fundação `0001` (DuplicateColumn em banco novo); routers por domínio (health, 11
  hubs, Central Jurídica, Mercado); CI GitHub Actions (backend migrations+pytest em pgvector
  descartável; frontend tsc+vitest). Validado: backend 626 passed/2 skipped, frontend 137 passed,
  migrations 0001→head RC=0. Modularização dos ~83 paths restantes segue contínua/incremental (ver
  nota em PROJECT-HISTORY sobre reexport obrigatório de handlers). Detalhes em `docs/PROJECT-HISTORY.md`.
- [ ] Fundação B1: Property/Opportunity, workflow, transições append-only, isolamento e invalidação.
- [ ] F1: classificação de modalidades e regras por modalidade/jurisdição.
- [ ] F0: radar, fontes autorizadas, ingestão, deduplicação, atualização e alertas.
- [ ] F2: cadastro e estruturação da oportunidade.
- [ ] F3: documentos, OCR, extração, evidências, versionamento e revisão.
- [ ] F4: Central Jurídica evoluída, fontes, vigência, jurisprudência e validação.
- [ ] F5: due diligence e checklists dinâmicos, preservando canonical_key.
- [ ] F6: motor financeiro, custos, cenários, sensibilidade, TIR e lance máximo.
- [ ] F7: valuation, comparáveis, liquidez, locação e mercado.
- [ ] F8: comitê, alçadas, score, hard stops e decisão auditável.
- [ ] F9: estratégia e preparação de participação/lance.
- [ ] F10: arrematação, pagamentos, obrigações e prazos.
- [ ] F11: transferência, registro, posse e ocupação.
- [ ] F12: regularização, reforma, orçamento e fornecedores.
- [ ] F13: locação, venda, receitas, despesas, ROI realizado e encerramento.
- [ ] Transversal: dashboard, dossiê, RBAC, auditoria, observabilidade, segurança, backups e runbooks.

### CICLO 3 — Validação e fechamento
- [ ] Testes unitários, integração, contrato e E2E por modalidade/fonte suportada.
- [ ] Testes de isolamento entre oportunidades do mesmo imóvel.
- [ ] Testes de idempotência, concorrência e append-only.
- [ ] Reconciliação independente dos cálculos financeiros.
- [ ] Revisão de fontes, vigência e regras jurídicas críticas.
- [ ] Testes de segurança e autorização.
- [ ] Backup e restauração em ambiente isolado.
- [ ] Validação de fluxos alternativos: descartado, cancelado, sem lance, não vencedor e arrematação desfeita.
- [ ] Documentação operacional, release checklist e limitações residuais.
- [ ] Relatório final de aceite 100%.

### Gates permanentes
- [ ] Preservar property 633, análises V1–V9, financial V1–V9, llm_runs, 27 canonical_key e Central Jurídica.
- [ ] Não executar backfill 0021 sem aprovação adicional + pg_dump.
- [ ] Não realizar chamadas pagas, LLM real ou scraping sem autorização.
- [ ] Não declarar concluído sem evidência de código + testes + integração + documentação.

---

## Status auditado (Ciclo 1 — 2026-11)

Resultado da auditoria factual (`docs/PROJECT-AUDIT-2026-11.md`). Itens **não apagados**; apenas
anotado o estado real por tema (evidência no documento de auditoria). Plano de execução em
`docs/IMPLEMENTATION-PLAN-100.md`.

- **P0 Diagnóstico/integridade/segurança** — diagnóstico ✅ (esta auditoria); matriz capacidade×gap ✅;
  separar modalidades ⬜ (`NAO_INICIADO`); estados de incerteza ✅ (engines); hard stops ⬜
  (`ESPECIFICADO`, só spec); preservação 633/27 keys ✅; GET/CRUD não dispara LLM ✅; **segurança/
  RBAC/LGPD ⬜ (`NAO_INICIADO`)**.
- **P0 Central Jurídica** — `IMPLEMENTADO (1.0)`; falta 2.0 (vigência/jurisprudência/aplicabilidade);
  cobertura dos 27 keys ✅ via `LegalRuleChecklistLink`.
- **P1 Workflow (F0–F13)** — `ESPECIFICADO` (0 código); F3/F4/F5/F6/F7 `IMPLEMENTADO` parcial via
  domínios atuais; F0/F1/F9/F12/F13 `NAO_INICIADO`.
- **P1 Checklists** — 27 keys preservados ✅; checklist dinâmico por modalidade ⬜.
- **P1 Custos/tributos** — `IMPLEMENTADO (parcial)`; falta parametrização por jurisdição/vigência,
  TIR/VPL/sensibilidade.
- **P1 Ocupação/posse** — `IMPLEMENTADO (parcial)` via Pós-Arrematação.
- **P2 Integrações/IA/UX** — RAG/citações ✅; conectores de ingestão ⬜; dashboards de oportunidade ⬜;
  limites de custo IA ⬜.
- **P0 Testes/preservação** — suíte ampla existe (50+ arquivos); faltam contrato OpenAPI,
  isolamento multi-oportunidade, concorrência no core, auth, E2E por modalidade; 633 preservado ✅.

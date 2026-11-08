# PRODUCT DASHBOARD — Radar Leilão

> **Painel executivo e status consolidado.** Baseado no **código efetivo** (HEAD `7f61667`,
> `20/09/2026`), não na documentação. Fonte detalhada: `docs/FEATURE-INVENTORY.md`. Nenhuma
> alteração de código/dados foi feita para produzir este painel.

## 1. Situação em uma frase
O **núcleo de "analisar um imóvel de leilão"** está sólido, testado e validado em E2E real (imóvel
633, V1–V9). A camada de **"conduzir o imóvel por um processo"** (workflow F0–F13, comitê, fases
tardias) e os **transversais** (auth/RBAC, modalidade, radar/descoberta, parâmetros fiscais) estão
ausentes ou em fundação. O produto é hoje uma **ferramenta de análise forte**, não ainda uma
**plataforma de workflow ponta a ponta**.

## 2. Metodologia dos indicadores (explícita)

- **Denominador:** 30 funcionalidades catalogadas em `FEATURE-INVENTORY.md` (lista canônica fechada).
- **Status por feature** atribuído por inspeção de código (endpoints, modelos, serviços, testes),
  não por documentação.
- **"Implementado"** = operacional no código. **"Validado"** = implementado **e** com teste
  automatizado verde e/ou E2E real. A distinção implementação × validação é mantida em todo o painel.
- **Percentuais** calculados como `contagem_do_status / 30`. Não há estimativa subjetiva de
  "esforço": cada feature conta como 1 unidade. Isso evita inflar número por documentação.
- **Limitações da métrica:** features têm tamanhos diferentes (contar 1:1 é uma simplificação
  consciente); "validado" depende da existência de teste — um teste fraco ainda conta como validado
  no nível de contrato. Por isso o painel traz também a leitura **qualitativa por fase** (§5).

## 3. Indicadores gerais (denominador = 30)

| Indicador | Contagem | % do escopo catalogado |
|---|---|---|
| Especificado (há spec/plano) | 30/30 (todas têm spec ou código) | 100% |
| Implementado (operacional, inclui parciais e validados) | 24/30 | 80% |
| — dos quais **Validados** (teste/E2E) | 12/30 | 40% |
| — dos quais **Parciais** | 11/30 | 37% |
| — **Em desenvolvimento** | 1/30 | 3% |
| Especificado sem código | 1/30 | 3% |
| Não iniciado | 5/30 | 17% |
| Com componente **bloqueado** (dependência externa) | 2/30 (B2, C2) | 7% |

> Leitura: **40% validado**, **37% implementado-parcial**, **17% não iniciado**. "Implementado de
> alguma forma" (validado + parcial + em desenvolvimento) = **80%**, mas isso **não** significa
> produto 80% pronto — significa que 80% das features catalogadas têm algum código operacional; a
> maturidade real por fase está em §5.

## 4. Quadro-resumo (concluídas / andamento / pendente / bloqueado)

| Categoria | Qtde | Features |
|---|---|---|
| **Concluídas e validadas** | 12 | Cadastro, RAG, Checklist Mestre, Risk, Verdict, Financeiro, Mercado, Ocupação, Evidências, Pós-arrematação, Leiloeiros, Frontend/dossiê |
| **Em andamento (parcial/dev)** | 12 | Cofre documental, OCR/extração, Agentes LLM, Histórico/incremental, Memória, Processos, Judicial, Central Jurídica, Due diligence, M0, B1 workflow, F8 comitê |
| **Pendente (não iniciado/especificado)** | 6 | Modalidade (F1), Radar/F0, Lance/F9, Saída/F12, Auth/RBAC, Parâmetros fiscais |
| **Com componente bloqueado** | 2 | Judicial/DataJud, Due diligence (RI/Prefeitura/Maps) |

## 5. Maturidade por fase do workflow (F0–F13) — leitura qualitativa

| Fase | Capacidade | Maturidade real (código) |
|---|---|---|
| F0 | Intake/descoberta/snapshot/dedupe | 🟡 Cadastro forte; **radar/descoberta/dedupe ausentes** |
| F1 | Classificação de modalidade | 🔴 Apenas campo livre (ESPECIFICADO) |
| F2 | Cofre documental + OCR | 🟢 Forte; falta validade/confidencialidade/supersedes; OCR off |
| F3 | Jurídico pré-leilão | 🟡 Matrícula/edital/processos/correlação OK; falta cadeia registral |
| F4 | Fiscal/condominial | 🟡 Débito genérico + frente PREFEITURA manual; falta detalhamento |
| F5 | Localização/inspeção | 🟡 Geocode + checklist; falta vistoria estruturada |
| F6 | Ocupação/posse | 🟡 Registro + pós-arrematação; falta classificação assistida |
| F7 | Viabilidade financeira | 🟢 Motor robusto; **falta TIR/VPL/sensibilidade e parâmetros fiscais** |
| F8 | Comitê/decisão | 🔴 Verdict existe, mas **não é comitê multidimensional com hard stops/decisão humana** |
| F9 | Lance/pagamento | 🔴 Ausente |
| F10 | Transferência/registro | 🟡 Pós-arrematação cobre etapas/custos; falta modelagem registral |
| F11 | Posse/regularização/reforma | 🟡 Posse/notificação OK; reforma sem modelo dedicado |
| F12 | Exploração/saída | 🔴 Ausente |
| F13 | Encerramento/dossiê | 🟡 Status/histórico OK; falta dossiê exportável + projetado×realizado |

Legenda: 🟢 forte · 🟡 parcial · 🔴 ausente/fraco.

## 6. Indicadores por módulo

| Módulo | Features | Validadas | Parciais | Pendentes | Leitura |
|---|---|---|---|---|---|
| A — Núcleo de Análise | 14 | 9 | 5 | 0 | 🟢 maduro e testado |
| B — Jurídico | 3 | 0 | 3 | 0 | 🟡 funcional, com bloqueios externos |
| C — Pós-aquisição | 2 | 1 | 1 | 0 | 🟡 pós-arrematação forte; DD parcial |
| D — Operação/fornecedores | 1 | 1 | 0 | 0 | 🟢 leiloeiros + credenciais seguras |
| E — Frontend | 1 | 1 | 0 | 0 | 🟢 dossiê + hubs testados |
| F — Fundação plataforma | 3 | 1 (M0) | 1 (B1) | 1 (F1) | 🟡 fundação em curso |
| G — Transversais/fases | 6 | 0 | 0 | 6 | 🔴 maior lacuna (auth, F0, F9, F12, fiscal) |

## 7. Principais entregas realizadas (evidência)
- **E2E real Caixa (imóvel 633):** V1–V9 com 5 agentes e LLM real; `llm_runs` preservados.
- **Checklist Mestre** com 27 `canonical_key`, versionado e rastreável.
- **Motores determinísticos** (financeiro, risco, veredito, mercado) com anti-dupla-contagem e
  "ausência ≠ zero/sem risco".
- **Central Jurídica** (biblioteca curada + referências contextuais por `canonical_key`).
- **Pós-arrematação** completo (etapas/custos/contatos/consultorias/minutas versionadas).
- **Leiloeiros** com credenciais cifradas (Fernet, falha-fechada) e reveal auditável.
- **Due diligence** 4 frentes (com integrações que falham-fechado sem credencial).
- **Ciclo 2 — Onda 0 (M0 + CI):** modularização em routers + guard-rail de contrato (99 paths) +
  pipeline GitHub Actions.
- **Ciclo 2 — Onda 1 (Opportunity + Workflow Engine puro):** domínio + migrations aditivas 0018/0019
  + engine determinístico F0–F13 + testes de isolamento.
- **Suíte:** 658 testes backend / 137 frontend; migrations 0001→0019 reversíveis.

## 8. Maturidade arquitetural
- **Pontos fortes:** separação clara entre **determinístico** (engines) e **LLM** (agentes); sistema
  sobe e opera **sem** `OPENAI_API_KEY` (degradação graciosa); integrações externas **falham-fechado**;
  rastreabilidade por evidência; migrations aditivas/reversíveis; contrato de API sob guard-rail (M0);
  CI automatizado.
- **Pontos fracos:** `main.py` ainda concentra ~83 rotas (monólito em modularização contínua);
  workflow/Opportunity **não ligados** à API (fundação pura); **sem auth/RBAC** (bloqueia uso
  multiusuário real); acoplamento de leitura em `services.py` (971 linhas) e `main.py` (2029 linhas).

## 9. Integrações
| Integração | Estado real |
|---|---|
| OpenAI (LLM/embeddings) | Opcional; sem chave → fallback textual/determinístico e `SEM_CHAVE` |
| Judicial API / DataJud | Consumidor HTTP implementado; **consulta real depende do serviço + credencial** (degrada gracioso) |
| Google Maps (geocode) | Opcional; sem key → `NAO_CONFIGURADO` (links externos sempre disponíveis) |
| RI Digital (registro) | **Sem cliente HTTP**; manual/`NAO_CONFIGURADO` |
| Prefeitura/IPTU | **Sem cliente HTTP**; registro manual de débito |
| Portais de leilão (F0) | **Não integrados**; backlog (termos/credenciais pendentes) |

## 10. Dívidas técnicas (priorizadas)
1. **Auth/RBAC inexistente** — bloqueia produção multiusuário; `actor` é texto livre. (Alta)
2. **Workflow não exposto** — engine puro da Onda 1 sem serviço/endpoints/UI; valor ainda não
   materializado. (Alta)
3. **Monólito `main.py`** (~83 rotas) — modularização contínua pendente. (Média)
4. **Parametrização fiscal ausente** — `COST_KEYS` fixas; sem jurisdição/vigência/fonte. (Média)
5. **OCR desligado** e extração dependente de LLM — matrícula escaneada não extrai sem provisão. (Média)
6. **Correlação `ALTA` inalcançável** — perfil do imóvel sem CPF/CNPJ do proprietário. (Média)
7. **`affected_checklist_keys` sempre vazio** — reanálise incremental não mira itens de checklist. (Baixa)
8. **KnowledgeMemory sem superfície HTTP** — serviço de memória não exposto/usado. (Baixa)
9. **Sem observabilidade** além de logs — sem métricas/tracing/alertas. (Média)
10. **Upload sem limite de tamanho/MIME** explícito (só extensão). (Média — segurança)

## 11. Principais riscos atuais
- **Confundir "análise" com "plataforma":** o núcleo analítico é forte, mas o workflow ponta a ponta
  (F8/F9/F12 + decisão humana) não existe — risco de superestimar a prontidão.
- **Dependências externas não habilitadas:** DataJud, Maps, RI, Prefeitura — sem credenciais/serviço,
  várias frentes ficam manuais (comportamento correto, mas limita automação).
- **Segurança para produção:** ausência de auth/RBAC e limites de upload é bloqueante para expor a
  múltiplos usuários.
- **Parâmetros fiscais:** qualquer número fiscal (IR/ITBI/emolumentos) exige fonte oficial + vigência;
  não podem ser fixados como constante (risco jurídico/financeiro).
- **Preservação do histórico:** evolução deve permanecer aditiva (nullable/legado); backfill (Gate 2)
  permanece bloqueado para não tocar V1–V9/633.

## 12. Caminho crítico para "produto ponta a ponta"
Workflow exposto (serviço + API + UA de oportunidades) → F8 comitê com hard stops e decisão humana →
F9 lance/pagamento → F12 saída → F13 dossiê exportável; em paralelo, **auth/RBAC** (bloqueante para
produção). Detalhe priorizado em `docs/ROADMAP-EXECUTION.md`.

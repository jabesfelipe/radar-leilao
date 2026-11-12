# WORKFLOW LEILÃO — END TO END (F0 → F13)

> **Situação (reestruturação documental): ATUALIZAR.** Este diagnóstico da "Fase Zero" afirma que a máquina de estados não existe.
> Hoje o workflow F0-F13 **está implementado** (`workflow_rules.py`, `workflow_engine.py`, `routers/opportunities.py`).
> Mapa atual: [modules/opportunities-workflow.md](../modules/opportunities-workflow.md). Mantido como descrição do workflow-alvo e
> do mapeamento fase a fase da época.

> **Fase Zero / diagnóstico.** Documento de planejamento. Nada implementado. Descreve o
> workflow-alvo do `PROMPT-KIRO-PLATAFORMA-COMPLETA.md` e mapeia, fase a fase, o que **já
> existe** no código vs o **gap**. Foco em leilão **extrajudicial de alienação fiduciária
> (Lei 9.514/97)**; fluxo judicial é trilha separada.

## Princípios do workflow (regras inegociáveis aplicadas a todas as fases)

- Evidência antes de conclusão; **ausência de resultado ≠ ausência de risco**.
- Separar: fato observado · documento · inferência · hipótese · estimativa · parecer.
- Toda conclusão material aponta fonte, documento/página/trecho, data-base, limitações,
  confiança e regra aplicada.
- Histórico append-only; correção gera nova versão + trilha before/after.
- GET/CRUD/navegação **não** disparam LLM, nova versão analítica nem custo externo.
- Integração sem credencial = `NAO_CONFIGURADO` (nunca simula sucesso).
- Mudança de edital/preço/matrícula/processo/ocupação/premissa **invalida aprovação** e
  exige revisão.

## Máquina de estados (alvo — ainda não existe)

Hoje não há um agregado de workflow. A base para construí-lo já existe: `DomainEvent` +
`EntityHistory` + `ImpactAnalyzer`/`IncrementalAnalysisService`. A proposta (épico B) é um
agregado por imóvel com estado por fase e **gates** de transição, **orquestrando** os
domínios existentes, sem substituí-los.

```
F0 Intake → F1 Triagem → F2 Documentos → F3 Jurídico → F4 Fiscal → F5 Localização
   → F6 Ocupação → F7 Financeiro → F8 Comitê ──(aprova)──► F9 Lance → F10 Registro
   → F11 Posse/Reforma → F12 Saída → F13 Encerramento
                        └──(reprova/descarta)──► F13 (ENCERRADO_COM_PENDENCIA/DESCARTADO)
```

Transições **não** são automáticas por IA: cada gate exige evidência e/ou decisão humana.

---

## Fases

### F0 — Intake e descoberta
- **Alvo:** capturar origem/URL, portal, identificador externo, credor, leiloeiro,
  modalidade, praça, datas, status, preço, avaliação, comissão, pagamento, endereço,
  matrícula, timestamp. Versionar snapshot; detectar mudança de edital/preço/data/status;
  deduplicar sem fundir ambíguos. Status: `CAPTURADO`, `DUPLICADO_POTENCIAL`,
  `DADOS_INSUFICIENTES`, `EM_TRIAGEM`.
- **Existe:** `Property`, `Auction`, `PropertySource`, cadastro completo
  (`POST /api/imoveis/completo`), `PropertyWizard.tsx`.
- **Gap:** snapshot versionado de intake, diff de mudança, dedupe, estados de intake.
- **Reuso:** `PropertySource` + `DomainEvent`/`EntityHistory` para snapshot/diff.

### F1 — Triagem e classificação
- **Alvo:** classificar `JUDICIAL` / `EXTRAJUDICIAL_ALIENACAO_FIDUCIARIA` /
  `EXTRAJUDICIAL_OUTRA_GARANTIA` / `VENDA_DIRETA` / `INDEFINIDO`, **exigindo evidência no
  edital/ato** (nunca inferir modalidade pela palavra "leilão"). Regras passam a variar por
  modalidade/UF/tipo/ocupação/finalidade.
- **Existe:** nada classifica modalidade hoje.
- **Gap (bloqueador estrutural):** campo `modality` + evidência + motor de regras por
  modalidade. É o destravador do resto (ver ROADMAP §5).
- **Reuso:** `AuctionNotice` + `extraction.py` + `Evidence`.

### F2 — Documentos e evidências
- **Alvo:** cofre versionado (edital/retificações, matrícula/ônus, contrato, notificações,
  avaliações, fotos, plantas, convenção, certidões, procurações, guias, comprovantes, auto/
  carta, registro). Metadados: emissor, origem, data, validade, período coberto, protocolo,
  hash, página, classificação, confidencialidade, versão. `supersedes` (nunca apagar
  substituído). OCR com página/trecho/confiança/revisão. Campo ausente = `NAO_LOCALIZADO`.
- **Existe (forte):** `Document`, `DocumentVersion` (hash, markdown, imutável), `DocumentChunk`
  (embedding + full-text), RAG híbrido, `extraction.py` (matrícula/edital com referência
  obrigatória por campo, `null` para ausência).
- **Gap:** campos `supersedes`, `valid_until`, `confidentiality`, `period_covered`,
  `protocol`; estado `NAO_LOCALIZADO` por campo; classificação documental ampliada.
- **Reuso:** toda a camada documental/RAG atual.

### F3 — Jurídico pré-leilão
- **Alvo:** ler edital integral + retificações; conferir matrícula (titularidade, alienação
  fiduciária, consolidação, cancelamentos, indisponibilidade, penhoras, hipotecas, usufruto,
  servidões, locação averbada, ações reais, restrições); cadeia registral; correspondência
  edital × matrícula × endereço × unidade × vaga × fração × área; intimação da mora; atos art.
  26/27 da Lei 9.514/97; processos (anulatórias, tutelas, possessórias, inventário, falência);
  distinguir encontrado/homônimo/correlação provável/confirmada. Resultado:
  `SEM_GAP_IDENTIFICADO_NAS_FONTES_CONSULTADAS`, `RISCO_CONTROLAVEL`, `PENDENCIA_RELEVANTE`,
  `RISCO_CRITICO`, `INVIAVEL`, `INCONCLUSIVO` — sempre com escopo.
- **Existe:** `PropertyRegistration`, `AuctionNotice`, `LegalProcess`/`ProcessMovement`,
  `legal_correlation.py` (homônimo×identidade), `DueDiligenceFront(MATRICULA/JUDICIAL)`,
  `judicial_integration.py` (DataJud), Central Jurídica 1.0.
- **Gap:** cadeia registral estruturada; conferência cruzada automatizada edital×matrícula;
  estados de resultado jurídico; vínculo forte a dispositivos da Central Jurídica.
- **Reuso:** todo o domínio jurídico + Central Jurídica.

### F4 — Fiscal / condomínio / operacional
- **Alvo:** IPTU, inscrição municipal, dívida ativa, exercícios, parcelamentos, certidão,
  sub-rogação, edital; condomínio detalhado (principal/multa/juros/honorários/rateios/ações/
  acordos/data-base); água/luz/gás (separar dívida pessoal de obrigação do imóvel); certidões
  contextualizadas (o que provam e o que não provam); zoneamento/tombamento/contaminação/
  desapropriação/regularidade/habite-se/área divergente.
- **Existe:** `Debt` (genérico, incl. IPTU/condomínio), `DueDiligenceFront(PREFEITURA)`,
  `finance.py` consome débitos.
- **Gap:** certidão contextual modelada; sub-rogação explícita; decomposição do débito
  condominial; urbanismo/zoneamento/habite-se.
- **Reuso:** `Debt` + frente PREFEITURA + motor financeiro.

### F5 — Localização / inspeção
- **Alvo:** geocodificação com fonte/precisão (não é confirmação cadastral); entorno (acesso,
  transporte, comércio, escolas, saúde, enchente, ruído, declividade, riscos ambientais);
  vistoria (fachada, áreas comuns, ocupação, conservação, danos, fotos datadas). Sem vistoria
  interna → declarar limitação; Street View não prova estado interno.
- **Existe:** `PropertyLocation`, `geocoding_client.py`, checklist de localização,
  `DueDiligenceFront(LOCALIZACAO)`.
- **Gap:** vistoria estruturada + limitação explícita de ausência de vistoria interna.
- **Reuso:** frente LOCALIZACAO + geocoding.

### F6 — Ocupação / posse
- **Alvo:** classificar (desocupado confirmado / proprietário-devedor / locatário / terceiro /
  incerto / conflitante); distinguir posse/propriedade/locação/comodato/usufruto; locação
  (contrato, prazo, averbação, preferência); negociação respeitosa, proposta voluntária,
  notificação revisada, mediação, medida judicial; **proibir autotutela** (coerção, corte de
  serviços, entrada forçada, troca de fechadura). Minutas são rascunhos para advogado. Taxa
  de ocupação art. 37-A só após validar incidência/beneficiário/marco/base/cumulação/
  jurisprudência. Não prometer liminar.
- **Existe:** `OccupancyAnalysis`, pós-arrematação (`OccupantContact`, `ContactAttempt`,
  `Consultancy*`, `NotificationDraft*`).
- **Gap:** taxonomia formal de ocupante/fundamento; simulador de taxa de ocupação validado;
  vínculo à Central Jurídica (art. 37-A, Lei 8.245/91).
- **Reuso:** domínio de ocupação + pós-arrematação + Central Jurídica.

### F7 — Viabilidade financeira
- **Alvo:** motor determinístico/explicável; cenários conservador/base/otimista; custos
  (lance, comissão, ITBI, registro/escritura, certidões, emolumentos/FUNREJUS/fundos/selos,
  tributos, condomínio, IPTU, débitos, advogado, desocupação, mudança, custas, reforma,
  regularização, seguro, utilidades, carregamento, custo de capital, corretagem, IR ganho de
  capital) **parametrizados por jurisdição/ato/base/vigência/fonte**; separar conhecido/
  estimado/cotação pendente/contingência; evitar dupla contagem; custo total/até
  regularização/posse/reforma/saída, break-even, preço máximo, margem, ROI, **TIR**, fluxo de
  caixa, **sensibilidade**. IR condicional a PF/PJ/regime.
- **Existe (forte):** `finance.py` (breakdown, resultado líquido, margem, ROI, break-even,
  preço máximo, cenários), `FinancialAnalysis`, premissas no `Auction`, anti-dupla-contagem.
- **Gap:** TIR/VPL/fluxo descontado; sensibilidade paramétrica; **custos parametrizados por
  jurisdição/ato/vigência** (hoje categorias fixas); memória de cálculo por fonte/data-base.
- **Reuso:** `finance.py` + `FinancialAnalysis` (estender, não reescrever).

### F8 — Comitê / decisão
- **Alvo:** score separado por dimensão (jurídico, documental, físico, ocupação, fiscal,
  mercado, financeiro, liquidez, execução); **hard stops que a média não mascara**; exibir
  argumentos/incertezas/bloqueadores/pendências/preço máximo/validade temporal; registrar
  decisão humana (responsável, data, justificativa, versão dos dados); invalidar aprovação em
  mudança relevante.
- **Existe:** `VerdictEngine` (veredito global) + `Risk` + `Analysis`.
- **Gap (importante):** score multidimensional; hard stops explícitos; registro de decisão
  humana; invalidação automática por evento. Hoje o veredito é um rótulo global, não um comitê.
- **Reuso:** `Risk`/`Verdict`/`verdict_engine.py` como insumos; `DomainEvent` para invalidação.

### F9 — Lance / pagamento
- **Alvo:** calendário, regras do portal, lance máximo aprovado, incrementos, comprovantes,
  horário, resultado; vencedor (pagamento/comissão/guias/prazos/assinatura/documentos);
  perdedor/cancelado/suspenso (encerrar com motivo). **Não** automatizar lances nem movimentar
  dinheiro.
- **Existe:** nada específico (apenas cadastro do leilão em `Auction`).
- **Gap (ausente):** modelo de lance/pagamento/resultado.
- **Reuso:** `Auction`, `Auctioneer`, `PortalAccess`, `PostAuctionCost`.

### F10 — Transferência / registro
- **Alvo:** auto/carta/termo, pagamento, ITBI, registro, exigências, prenotação, matrícula
  atualizada, baixa de ônus, titularidade; conferir adquirente/fração/unidade. Separar
  pagamento/título/registro; não declarar propriedade registrada sem evidência registral.
- **Existe:** Pós-Arrematação (`PostAuction`, `PostAuctionStage` incl. `REGISTRO`,
  `PostAuctionCost`).
- **Gap:** modelagem registral formal (prenotação, baixa de ônus, matrícula pós-registro).
- **Reuso:** Pós-Arrematação + `PropertyRegistration`.

### F11 — Posse / regularização / reforma
- **Alvo:** entrega voluntária/judicial, chaves, termo, vistoria, fotos, medidores;
  regularização municipal/registral/condominial, averbação, habite-se, licenças; reforma
  (escopo, orçamento, fornecedores, contratos, notas, medições, aditivos, cronograma, aceite,
  ART/RRT). Posse física ≠ regularidade documental.
- **Existe:** pós-arrematação (etapas/custos/minutas).
- **Gap:** domínio de **reforma** (orçamento/fornecedor/contrato/medição/aceite) e
  **regularização** (habite-se/averbação/licenças) dedicados.
- **Reuso:** `PostAuctionStage`/`PostAuctionCost`/`Consultancy*`.

### F12 — Exploração / saída
- **Alvo:** estratégia (venda / reforma-e-venda / locação / manter); locação (contrato,
  garantias, vistoria, administração, vacância, tributos); venda (avaliação, comparáveis,
  preço mínimo, corretagem, documentação, marketing, propostas, contrato, recebimento,
  registro); comparar **projetado × realizado** (lucro, ROI, TIR, prazo, desvio).
- **Existe:** projeção (`finance.py`), `MarketComparable`.
- **Gap (ausente):** modelo de estratégia de saída, contrato de venda/locação, resultado
  realizado vs projetado.
- **Reuso:** `finance.py` + `MarketComparable` + `PostAuction`.

### F13 — Encerramento
- **Alvo:** dossiê final exportável; status `VENDIDO`/`LOCADO`/`MANTIDO`/`DESCARTADO`/
  `CANCELADO`/`PERDIDO_NO_LEILAO`/`ENCERRADO_COM_PENDENCIA`; retrospectiva/indicadores;
  histórico não sobrescrito.
- **Existe:** `Property.status`, histórico (`EntityHistory`, `Analysis`, `Verdict`).
- **Gap:** estados finais; export de dossiê; retrospectiva projetado×realizado.
- **Reuso:** `Property`/`Verdict`/`Analysis`/`EntityHistory`.

---

## Resumo de prontidão

| Fase | Estado | Épico |
|---|---|---|
| F0 | 🟡 Parcial | B |
| F1 | 🔴 Ausente | B |
| F2 | 🟢 Forte (lacunas de metadados) | C |
| F3 | 🟡 Parcial | F / E |
| F4 | 🟡 Parcial | F |
| F5 | 🟡 Parcial | F |
| F6 | 🟡 Parcial | G |
| F7 | 🟢 Forte (lacunas TIR/sensibilidade/parametrização) | H |
| F8 | 🔴 Parcial-fraco | I |
| F9 | 🔴 Ausente | I |
| F10 | 🟡 Parcial | J |
| F11 | 🟡 Parcial | K |
| F12 | 🔴 Ausente | K |
| F13 | 🟡 Parcial | L |

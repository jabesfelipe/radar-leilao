# Due Diligence integrada (4 frentes)

Evolução reuse-first do Radar Leilão: uma investigação integrada por imóvel
cobrindo Matrícula/ônus, Processos Judiciais, Prefeitura/IPTU e Localização,
rastreável no dossiê e na linha do tempo. Nenhum módulo foi duplicado e a
arquitetura não foi reescrita.

## Princípio de confiabilidade

`EVIDÊNCIA ENCONTRADA ≠ CORRELAÇÃO COM O IMÓVEL ≠ FATO CONFIRMADO`. A **ausência de
resultado nunca é tratada como ausência de risco**. Integrações externas sem
credencial aparecem como `NAO_CONFIGURADO` — o sistema **nunca simula** uma consulta
bem-sucedida.

## Reutilização (o que NÃO foi duplicado)

| Frente | Reusa | Novo |
|---|---|---|
| Matrícula/ônus | `PropertyRegistration`, extração documental (MATRICULA), `Evidence`/`EvidenceLink`, endpoints `/matricula`, import/OCR | estado da frente |
| Judicial | `JudicialIntegrationService`/`JudicialApiClient`/`legal_correlation`, `LegalProcess`/`ProcessMovement`, `/processos`, `/processos/consultar` | — |
| Prefeitura/IPTU | `Debt` (category=IPTU) + `/dividas` + `build_finance` (IPTU já roteia no breakdown, somado 1×) | registro manual rastreável; config |
| Localização | `Evidence`, `record_event`, checklist `REGIAO_SERVICOS` | **nova tabela** geo + checklist de localização |
| Comum | `record_event`/`record_history` → `/historico`; `RiskEngine`/`VerdictEngine` (puros) | estado por frente + orquestrador + config |

## Entidades novas (migration `0016_due_diligence`)

- `due_diligence_fronts`: estado por `(property_id, frente)` — status, fonte, modo
  (manual/automático), última consulta, pendências, achados, revisão humana.
- `property_locations`: 1 por imóvel — coordenadas (quando geocodificadas),
  precisão/fonte, links Maps/Street View e o checklist de localização (JSON).

Estados de frente: `NAO_INICIADO`, `NAO_CONFIGURADO`, `AGUARDANDO_ACAO`, `EM_EXECUCAO`,
`CONSULTADO`, `SEM_OCORRENCIA`, `CONCLUIDO_COM_PENDENCIAS`, `FALHOU`, `INDISPONIVEL`,
`NECESSITA_REVISAO`. A UI distingue visualmente cada um (nunca usa "sem riscos").

## Endpoints

- `GET /api/imoveis/{id}/due-diligence` — visão consolidada das 4 frentes (leitura).
- `GET /api/imoveis/{id}/localizacao` — localização + checklist + links + status.
- `PUT /api/imoveis/{id}/localizacao` — coordenadas manuais, confirmação, observações,
  checklist (BOM/REGULAR/RUIM/NAO_VERIFICADO).
- `POST /api/imoveis/{id}/localizacao/geocodificar` — geocodifica via Google Maps
  quando configurado; sem chave retorna `NAO_CONFIGURADO` (não inventa coordenadas).
- `POST /api/imoveis/{id}/due-diligence/prefeitura/debito` — registro manual de débito
  municipal reutilizando `Debt` (não duplica custo).
- `POST /api/imoveis/{id}/due-diligence/{frente}/revisar` — marca a frente como revisada.

Todas as mutações emitem `DomainEvent` + `EntityHistory` (tipos `LOCALIZACAO_*`,
`DILIGENCIA_FRENTE_*`) → aparecem em `/historico` e na aba Histórico.

## Sinais em Checklist/Riscos/Veredito (determinístico, sem LLM)

Pendências de due diligence (ônus a validar, localização sem confirmação, débito
não confirmado) marcam o item de checklist correspondente como **ATENCAO** na
execução corrente, com evidência — nunca `CONFIRMADO` automático, preservando
estados manuais. O `RiskEngine`/`VerdictEngine` (puros) então consideram esses
itens sem criar nova versão de análise nem acionar LLM.

Mapa frente → item de checklist reutilizado: MATRICULA→`CONSOLIDACAO_REGISTRADA`,
JUDICIAL→`ACAO_QUESTIONAMENTO`, PREFEITURA→`RESPONSABILIDADE_DEBITOS`,
LOCALIZACAO→`REGIAO_SERVICOS`.

## Como configurar cada fonte

Todas as integrações são **opcionais** e defaultam para desativado (o app sobe sem
nenhuma). Variáveis em `.env` (nunca versione uma chave real; nunca exponha no frontend):

| Fonte | Variáveis | Estado sem credencial |
|---|---|---|
| Google Maps (geocode/Street View) | `GOOGLE_MAPS_API_KEY`, `GOOGLE_MAPS_TIMEOUT_SECONDS` | links externos + registro manual de coordenadas |
| Registro de Imóveis (RI Digital) | `REGISTRO_IMOVEIS_BASE_URL`, `REGISTRO_IMOVEIS_API_KEY` | importação manual de PDF/certidão (com OCR) |
| Prefeitura/IPTU/valor venal | `PREFEITURA_API_BASE_URL`, `PREFEITURA_API_KEY` | cadastro manual rastreável |
| Cache de consulta | `DUE_DILIGENCE_CACHE_HOURS` (default 24) | — |

Requisitos do Google Maps Platform: API key com faturamento habilitado, quotas e
restrições de domínio conforme os termos de uso
(https://developers.google.com/maps/documentation). O RI Digital
(https://ridigital.org.br/) e os serviços municipais normalmente exigem
contratação/autorização e podem ter autenticação/CAPTCHA — não são contornados.

## Integrações: estado real

- **Judicial (DataJud via Judicial API)**: integrada e já em produção (HTTP, httpx),
  com degradação graciosa.
- **Google Maps (geocode/Street View)**: cliente real implementado e testado (parsing
  validado com httpx MockTransport: OK, ZERO_RESULTS, timeout). Operacional mediante
  `GOOGLE_MAPS_API_KEY`. Sem a chave: `NAO_CONFIGURADO` + links externos.
- **RI Digital / Prefeitura**: preparadas para configuração; sem credencial, fluxo
  manual funcional. Consulta automática **não** declarada como realizada sem a fonte.

Nenhuma consulta externa paga foi disparada; nenhuma credencial foi assumida.

## Frontend

Aba **Due Diligence** no dossiê (`DueDiligenceSection`, serviço `dueDiligence.ts`)
com 4 cards (Matrícula/ônus, Processos, Prefeitura/IPTU, Localização), estados visuais
distintos, checklist de localização, links externos e status de integração.

## Testes (resultados reais)

- Backend: `tests/test_due_diligence.py` — **12 passed** (orquestrador 4 frentes;
  localização CRUD/persistência/checklist; lat/lng inválida → 422; geocode sem key →
  `NAO_CONFIGURADO` sem inventar coordenadas; prefeitura reusa `Debt` sem duplicar
  custo; sinal de localização → checklist `ATENCAO`; eventos na linha do tempo;
  revisão de frente; cliente de geocode puro + httpx mock OK/ZERO_RESULTS/timeout).
- Suíte backend completa: **613 passed, 2 skipped**.
- Frontend: `tsc --noEmit` sem erros + `vitest run` **132 passed (21 arquivos)**
  (inclui `DueDiligenceSection.test.tsx`).
- Persistência validada ao vivo: após `docker compose build` + `restart backend`, os
  dados de localização sobreviveram. Imóvel 633 intacto (9 análises V1–V9, zero V10).

## Limitações conhecidas

- Geocodificação/Street View exigem Google Maps API key com faturamento.
- RI Digital e serviços municipais dependem de contratação/autorização; enquanto não
  configurados, operam por importação/cadastro manual.
- A frente Judicial depende da disponibilidade e dos campos suportados pela Judicial
  API/DataJud; pesquisa por partes pode não estar disponível em toda fonte.

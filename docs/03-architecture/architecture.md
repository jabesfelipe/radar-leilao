# Arquitetura

Visão da arquitetura **atual** do Radar Leilão, com 11 diagramas Mermaid. Convenção: elementos com borda tracejada e rótulo
"(planejado)" ou "(sem cliente)" **não existem** hoje ou não têm integração implementada. Substitui o antigo `ARCHITECTURE.md`
(arquivado: mostrava proxy 80/443 com HTTPS e 143 paths, e o estado atual é HTTP 80 e 144 paths).

## Visão em uma tabela

| Camada | Tecnologia |
|---|---|
| Frontend | React 19, Vite 6, TypeScript 5.7, lucide-react; testes com vitest 2.1.8 e testing-library; **sem react-router** |
| Backend | Python 3.12, FastAPI 0.115, uvicorn, SQLAlchemy 2.0, Alembic 1.14, pydantic-settings |
| IA | LangChain 0.3, LangGraph 0.2, OpenAI (gpt-4o-mini, text-embedding-3-small), MarkItDown, Tesseract (OCR desabilitado) |
| Banco | PostgreSQL 16 com pgvector (`pgvector/pgvector:pg16`) |
| Proxy | nginx 1.27-alpine (portão por cookie, rate limit de login, `/docs` oculto) |
| Deploy | Docker Compose em uma VPS Contabo; imagens no GHCR; GitHub Actions por tag |

## 1. Contexto do sistema

```mermaid
flowchart LR
  U["Analista / investidor"] -->|navegador, HTTP| R["Radar Leilão"]
  R -->|embeddings e LLM, opcional| O["OpenAI"]
  R -->|consulta de processos| J["Judicial API própria sobre DataJud"]
  R -->|geocodificação, opcional| G["Google Geocoding"]
  R -.->|sem cliente| RI["Registro de Imóveis"]
  R -.->|sem cliente| PM["Prefeituras"]
  R -.->|planejado| P["Portais de leilão"]
  DEV["Desenvolvedor"] -->|tag vX.Y.Z| GH["GitHub Actions e GHCR"]
  GH -->|deploy por SSH| R
```

## 2. Containers (produção, `docker-compose.prod.yml`, projeto `radar-prod`)

```mermaid
flowchart TB
  B["Navegador"] -->|HTTP porta 80| PX["proxy nginx 1.27, 64 MB"]
  PX -->|"/"| FE["frontend nginx com SPA, 64 MB"]
  PX -->|"/api"| BE["backend FastAPI, uvicorn 2 workers, 2 GB"]
  BE --> PG[("postgres 16 + pgvector, 2 GB")]
  WK["worker: python -m app.worker_main, 1 GB"] --> PG
  MG["migrate (profile, one-shot)"] --> PG
  BE --- ST[("volume backend_storage")]
  WK --- ST
  PG --- PD[("volume postgres_data")]
```

O desenvolvimento (`docker-compose.yml`) expõe postgres 5432, backend 8000, `judicial_api` 8010 e frontend 5173; a `judicial_api`
**não** está no compose de produção.

## 3. Backend

```mermaid
flowchart TB
  M["main.py: cerca de 112 rotas"] --> SV
  RT["11 routers: health, hubs, legal_central, market, admin, debts, auth, opportunities, dashboard, monitoring, document_files"] --> SV
  subgraph SV["Serviços e motores"]
    FIN["finance.py e estimates_service.py"]
    RSK["risk_engine.py e verdict_engine.py"]
    CHK["checklist.py e modality_rules.py"]
    WF["workflow_rules.py e workflow_engine.py"]
    LEG["legal_catalog.py e legal_service.py"]
  end
  SV --> AI["ai: gateway, agents e grafo LangGraph"]
  SV --> RAG["rag e documents"]
  RAG --> STG["storage: local ou S3"]
  SV --> DB["models.py, SQLAlchemy e Alembic"]
  AUTH["auth.py e authz.py: JWT e RBAC"] --> RT
```

## 4. Frontend

```mermaid
flowchart TB
  A["App.tsx: roteamento manual com pushState e popstate"] -->|sem sessão| L["LoginPage"]
  A --> H["Hubs: dashboard, oportunidades, documentos, jurídico, financeiro, mercado, ocupação, checklist, riscos, veredito, histórico"]
  A --> PD["PropertyDetailPage com 18 seções"]
  A --> AU["AuctioneersPage"]
  A --> AD["AdminPage com 6 abas"]
  H & PD & AU & AD --> S["services: chamadas à API"]
  S --> SE["session.ts: installAuthFetch injeta Bearer em /api"]
```

## 5. Persistência

```mermaid
erDiagram
  PROPERTIES ||--o{ AUCTIONS : tem
  PROPERTIES ||--o{ DOCUMENTS : tem
  DOCUMENTS ||--o{ DOCUMENT_VERSIONS : versoes
  DOCUMENT_VERSIONS ||--o{ DOCUMENT_CHUNKS : chunks
  PROPERTIES ||--o{ EVIDENCES : evidencias
  PROPERTIES ||--o{ CHECKLIST_EXECUTIONS : execucoes
  CHECKLIST_EXECUTIONS ||--o{ CHECKLIST_RESULTS : resultados
  CHECKLIST_ITEMS ||--o{ CHECKLIST_RESULTS : item
  PROPERTIES ||--o{ LEGAL_PROCESSES : processos
  LEGAL_PROCESSES ||--o{ PROCESS_MOVEMENTS : movimentacoes
  PROPERTIES ||--o{ COSTS : custos
  PROPERTIES ||--o{ DEBTS : debitos
  PROPERTIES ||--o{ FINANCIAL_ANALYSES : financeiro
  PROPERTIES ||--o{ RISKS : riscos
  PROPERTIES ||--o{ ANALYSES : analises
  PROPERTIES ||--o{ VERDICTS : vereditos
  PROPERTIES ||--o| POST_AUCTIONS : pos_arrematacao
  AUCTIONEERS ||--o{ PORTAL_ACCESSES : portais
```

São 60 tabelas e 23 migrations (`0001_fundacao_radar` a `0023_usuarios`); o diagrama mostra o núcleo. Ver [data-model.md](data-model.md).

## 6. Autenticação e autorização

```mermaid
sequenceDiagram
  participant N as Navegador
  participant P as Proxy nginx
  participant B as Backend
  N->>P: GET /acesso?k=GATE_KEY
  P-->>N: cookie radar_gate
  N->>P: POST /api/auth/login (e-mail e senha)
  P->>B: encaminha (rate limit 10 por minuto)
  B-->>N: JWT HS256, validade 480 min
  N->>N: localStorage radar.auth.token
  N->>P: requisições /api com Authorization Bearer
  P->>B: exige cookie do portão, senão 403
  B->>B: RBAC por permissão (rotas protegidas)
  B-->>N: 401 limpa a sessão e emite radar:unauthorized
```

Duas camadas independentes: o portão do proxy (todas as rotas) e o JWT com RBAC (apenas as rotas protegidas; 148 de 184 rotas não exigem credencial no backend).

## 7. Análise de oportunidade (workflow)

```mermaid
stateDiagram-v2
  [*] --> F0_INTAKE
  F0_INTAKE --> F1_TRIAGEM
  F1_TRIAGEM --> F2_DOCUMENTOS
  F2_DOCUMENTOS --> DD: due diligence paralela
  state DD {
    F3_JURIDICO_REGISTRAL
    F4_FISCAL_OPERACIONAL
    F5_LOCALIZACAO_INSPECAO
    F6_OCUPACAO_POSSE
    F7_VIABILIDADE_FINANCEIRA
  }
  DD --> F8_COMITE_DECISAO
  F8_COMITE_DECISAO --> F9_LANCE_PAGAMENTO: decisão APROVADA
  F9_LANCE_PAGAMENTO --> F10_TRANSFERENCIA_REGISTRO
  F10_TRANSFERENCIA_REGISTRO --> F11_POSSE_REGULARIZACAO
  F11_POSSE_REGULARIZACAO --> F12_EXPLORACAO_SAIDA
  F12_EXPLORACAO_SAIDA --> F13_ENCERRAMENTO
  F9_LANCE_PAGAMENTO --> PERDA: não arrematou
  F13_ENCERRAMENTO --> [*]
```

DESCARTE é possível a partir de qualquer fase exceto F13; hard stops bloqueiam o avanço; eventos de invalidação reabrem fases.

## 8. Análise financeira

```mermaid
flowchart LR
  PR["Premissas e custos do imóvel"] --> FM["finance.py: build_finance"]
  DB["Débitos e despesas pós-arrematação"] --> FM
  AU["Leilão: lance, avaliação, comissão"] --> FM
  PA["Parâmetros administráveis"] --> FM
  FM --> CT["Custo total sem dupla contagem"]
  CT --> RS["Resultado líquido, margem, ROI, break-even"]
  CT --> PM["Preço máximo por meta"]
  FM -->|custo ausente| PV["Resultado provisório: DESCONHECIDO"]
  RS --> FA[("financial_analyses versionadas")]
```

Cenário BASE implementado; OTIMISTA e PESSIMISTA, TIR/VPL e sensibilidade são planejados.

## 9. Análise documental e jurídica

```mermaid
flowchart TB
  UP["Upload do documento"] --> VS["Versão imutável com hash"]
  VS --> MD["MarkItDown, OCR se habilitado"]
  MD --> CH["Chunks"]
  CH --> EM["Embeddings (precisa de OPENAI_API_KEY)"]
  EM --> RG["Busca híbrida 0,7 vetorial e 0,3 textual"]
  CH --> RG
  RG --> AG["Agentes: documental, jurídico, financeiro, mercado, checklist"]
  AG -->|sem chave| SC["status SEM_CHAVE"]
  AG --> EV["Evidências"]
  EV --> CK["Checklist"]
  CJ["Central Jurídica: 5 fontes, 11 dispositivos, 8 regras"] --> CK
  JD["Judicial API: processos"] --> CK
  CK --> RK["Riscos"]
  RK --> VD["Veredito"]
```

## 10. Integrações

```mermaid
flowchart LR
  BE["Backend"] -->|"existe, opcional"| OA["OpenAI"]
  BE -->|"existe, requer X-API-Key"| JA["judicial_api -> DataJud"]
  BE -->|"existe, opcional"| GE["Google Geocoding"]
  BE -->|"existe, local ou S3"| S3["Storage"]
  BE -.->|"sem cliente"| RI["Registro de Imóveis"]
  BE -.->|"sem cliente"| PF["Prefeituras"]
  BE -.->|"manual-assistido"| DP["Provider de débitos"]
```

Detalhes em [integrations.md](integrations.md).

## 11. Infraestrutura e deploy

```mermaid
flowchart LR
  TG["git push tag vX.Y.Z"] --> VT["validate-tag"]
  VT --> CI["ci.yml reutilizado"]
  CI --> PB["publish: build e push GHCR"]
  PB --> DP["deploy: SSH como usuário radar"]
  DP --> RL["release.sh"]
  RL --> DS["deploy.sh auto: backup, migrate, up, smoke"]
  DS --> VPS["VPS Contabo: Docker Compose radar-prod"]
```

Operação: [../04-operations/infrastructure.md](../04-operations/infrastructure.md) e [../04-operations/github-actions.md](../04-operations/github-actions.md).

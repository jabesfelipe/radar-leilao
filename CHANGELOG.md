# Changelog

Formato: uma seção por versão publicada (tag `vX.Y.Z` na `main`). Datas no fuso de Brasília.

## v1.0.5 — 2026-11-14

Release operacional: primeira implantação na VPS com a IA (OpenAI) ativada. O código da aplicação é o da v1.0.4.

- VPS de homologação (`13.140.151.74`, HTTP) atualizada de v1.0.3 para v1.0.5 pelo `release.yml`, com backup do banco e
  dos documentos e a migration `0025_evidencia_origem_forca`.
- IA no `.env.prod` da VPS: `gpt-4o-mini`, `text-embedding-3-small`, teto mensal de US$ 0,50, teto por análise de
  US$ 0,10, 1.500 tokens de saída, `LLM_REQUIRE_BUDGET=true`, `LLM_REDACT_PII=true`. A chave fica só no `.env.prod`.
- `REQUIRE_HTTPS=false` mantido temporariamente: **só dados sintéticos ou documentos sanitizados** nesse ambiente.
- Rollback: `alembic downgrade 0024_analysis_version_unique` e `scripts/prod/rollback.sh` (volta para a v1.0.3), ou o
  backup gerado pelo deploy em `/opt/radar-backups`.

## v1.0.4 — 2026-11-14

Qualidade da análise por IA, rastreabilidade das evidências e homologação mobile.

### Funcionalidades

- **Rastreabilidade das evidências.** Cada evidência informa a origem (`DOCUMENTO`, `CADASTRO`, `CÁLCULO`, `INFERÊNCIA`) e a força da citação. Citações são validadas contra o texto do documento do próprio imóvel; trecho inexistente ou que não contém o valor afirmado é rebaixado ou descartado (`backend/app/citations.py`, migration `0025_evidencia_origem_forca`).
- **Extração estruturada com referência.** Campos da matrícula e do edital trazem trecho literal e posição no documento; falhas parciais ficam marcadas campo a campo.
- **Confronto documental determinístico** entre matrícula, edital e cadastro (`backend/app/document_comparison.py`), sem custo de IA.
- **Agentes**: regras explícitas de origem, roteiro documental e estados do checklist; pergunta do checklist não é aceita como evidência.
- **Frontend**: selos de origem e força das evidências e exibição do confronto documental no Veredito.

### Correções

- **Orçamento de IA com falha segura**: `LLM_REQUIRE_BUDGET=true` bloqueia chamadas pagas sem teto configurado; custo de resposta truncada contabilizado; modelo sem preço cadastrado é bloqueado.
- **Saída estruturada por function calling** (fim das respostas JSON truncadas).
- **Privacidade**: CPF mascarado também sem formatação; teste do payload realmente enviado ao provider.
- **Privacidade/estabilidade no detalhe do imóvel** (achado na homologação final com IA real): `GET /api/imoveis/{id}` devolvia o objeto ORM em `imovel`, e a serialização incluía todo relacionamento carregado (documentos, chunks com texto bruto sem máscara, caminho do arquivo, evidências sem máscara). Com chunks indexados (embedding) a resposta virava HTTP 500. Agora `imovel` traz só as colunas do imóvel (107 kB → 0,6 kB no caso-01). Teste: `test_property_detail_payload.py`.
- **Isolamento de evidências**: dívida, processo, matrícula, edital, ocupação, débito normalizado, estimativa condominial e modalidade da oportunidade recusam (422) `evidence_id` de outro imóvel ou inexistente. Antes, o imóvel A podia citar evidência do imóvel B. Teste: `test_evidence_ownership.py`.
- **Agente checklist**: `kind='pendente'` (e sinônimos de "não identificado") vira `ausencia` em vez de invalidar todas as findings do agente; valores livres continuam rejeitados.
- **Mobile** (`34f7976`): até 680px a topbar esconde nome/perfil do usuário (a 360px o título virava "C…") e os filtros de Oportunidades passam a ter 44px de altura.
- **Release**: o job de deploy do `release.yml` só roda com a variável de repositório `DEPLOY_ENABLED=true`. Sem ela, a tag valida, testa e publica as imagens no GHCR, mas não altera a VPS.

### Testes adicionados

- Backend: `test_citations`, `test_evidence_traceability`, `test_extraction_references`, `test_document_comparison`, `test_privacy_payload`, `test_budget_pricing`, `test_agent_contract_tolerance`.
- E2E: viewport 1920x1080 e `release.spec.ts` (capturas e checagens de dashboard, menu, imóveis, wizard e seções do detalhe em 360x800, 390x844, 412x915 e 1366x768).

### Resultados desta release

Detalhes em `docs/06-quality/homologacao-v1.0.4/RELEASE-v1.0.4.md`.

- Backend: 1219 passed, 3 skipped (2 DataJud real opt-in, 1 sem `.git` na cópia). Frontend: tsc 0 erros, 182/182, build OK.
- E2E Playwright: 196 passed, 7 skipped (IA paga, desligada por padrão), 0 falhas, em 360×800 a 1920×1080.
- IA real (caso-01, duas execuções): 5/5 agentes, financeiro igual ao gabarito, veredito NÃO ARREMATAR, citações 100% válidas, 0 alucinações detectadas, fatos 11/20 e 15/20, US$ 0,0071 e 0,0077 por execução.
- Isolamento: 19/19 verificações de acesso cruzado OK na API real. Nenhum segredo no histórico, arquivos, logs ou relatórios.

### Configuração necessária

- `.env` (nunca versionado): `OPENAI_API_KEY`, `LLM_BUDGET_USD_MONTH`, `LLM_BUDGET_USD_PER_ANALYSIS`, `LLM_MAX_OUTPUT_TOKENS`, `LLM_REQUIRE_BUDGET=true`, `LLM_REDACT_PII=true`. Ver `.env.example` e `.env.prod.example`.
- Migration nova: `0025_evidencia_origem_forca` (aplicada por `alembic upgrade head`; reversível com `downgrade -1`, verificado no CI).

### Limitações conhecidas

- A VPS continua na v1.0.3, só com HTTP. **Não usar documentos reais** até HTTPS, `REQUIRE_HTTPS=true`, backup e rollback conferidos (`docs/06-quality/homologacao-v1.0.4/PLANO-HTTPS-VPS.md`).
- A IA real foi validada só com o caso sintético `e2e/fixtures/caso-01`; a cobertura de fatos não é total (ver relatório da homologação).
- Validação em aparelho físico ainda depende de teste manual (`docs/HOMOLOGACAO-MOBILE-DESKTOP.md`).

### Rollback

- Código: a v1.0.3 continua disponível pela tag `v1.0.3` (`77ded35`); imagens `backend:v1.0.3`/`frontend:v1.0.3` no GHCR.
- Banco: `alembic downgrade 0024_analysis_version_unique` remove só as colunas novas de origem/força.
- VPS: procedimento em `docs/GITHUB-ACTIONS-DEPLOY.md` §8.

## v1.0.3 — 2026-11-14

Organização dos artefatos e do versionamento dos testes E2E (PR #4).

## v1.0.2 — 2026-11-13

Security hardening (PR #1, integração OpenAI).

## v1.0.1 — 2026-11-12

Corrige a rolagem do menu lateral no mobile.

## v1.0.0 — 2026-11-11

Primeira versão publicada.

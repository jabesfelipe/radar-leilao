# 06 — Qualidade

## Estratégia de testes

| Nível | Onde | O que cobre |
|---|---|---|
| Unidade e integração do backend | `tests/test_*.py` (pytest, PostgreSQL + pgvector) | motores (finance, risk, verdict, workflow, modalidades), API, RAG, worker, storage, auth, Central Jurídica, débitos, pós-arrematação |
| Contrato da API | `tests/contract/test_openapi_contract.py` e `openapi_baseline.json` | 144 paths; mudança de API exige atualizar o baseline |
| Política de release | `tests/test_release_workflow_policy.py` | somente `ci.yml` e `release.yml`; scripts 100755 |
| Isolamento por oportunidade | `tests/test_opportunity_isolation.py`, `tests/test_rag_opportunity_isolation.py` | dados de uma oportunidade não vazam |
| Fluxos ponta a ponta (API) | `tests/test_e2e_financeiro.py`, `test_e2e_oportunidade.py`, `test_juridico_e2e_http.py`, `test_integration_flows.py` | cenários completos via HTTP |
| Judicial API | `tests/judicial/` | módulo `judicial_api/` |
| Frontend | vitest + testing-library | componentes e serviços (27 arquivos) |
| CI | `.github/workflows/ci.yml` | migrations `0001`→head, reversibilidade, compose, nginx, scripts, actionlint, build das imagens |

Como executar: [../05-development/testing.md](../05-development/testing.md).

## Números atuais

Último resultado registrado antes desta reestruturação (**não reexecutado nesta missão documental**, que não altera código):

- backend: 807 passed, 2 skipped, mais o teste de política de release (main, antes do hardening);
- backend na branch de hardening: 964 passed, 2 skipped (PostgreSQL 16.15 + pgvector local; os 2 skips são testes reais do DataJud, desabilitados de propósito); frontend: 29 arquivos, 169 testes, `tsc` e build de produção OK;
- API: 144 paths (baseline); 184 rotas; **na branch de hardening todas passam pelo portão global** (2 públicas);
- banco: 69 tabelas num banco novo por `alembic upgrade head` (igual à produção), 23 migrations em `main` (head `0023_usuarios`) e **24 na branch** (`0024_analysis_version_unique`).

Marcador de testes de segurança: `@pytest.mark.security_gate` roda com o portão real; os demais testes usam o bypass descrito em [testing.md](../05-development/testing.md).

Documentos antigos citam outros números (527 passed, 99 a 143 paths, migrations 0017 e 0019); todos estão superados. Para números novos, rode os comandos e cite data e fonte.

## Lacunas de cobertura conhecidas

- Não há medição de cobertura de código (nenhum relatório `coverage` configurado no CI).
- O CI não executa testes em navegador real (apenas vitest); a correção da rolagem do menu mobile foi validada em WebKit fora do CI.
- Rollback, interrupção por backup falho e bootstrap foram validados por simulação local, não na VPS real.
- No CI, LLM e integrações externas ficam desligados (conforme `ci.yml`).

Limitações do produto: [known-limitations.md](known-limitations.md).

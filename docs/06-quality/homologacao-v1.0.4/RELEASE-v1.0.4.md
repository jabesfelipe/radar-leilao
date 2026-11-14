# Release v1.0.4: fechamento técnico

Data: 2026-11-14. Detalhe de mudanças em [CHANGELOG.md](../../../CHANGELOG.md).

## Estado do repositório

| Item | Valor |
|---|---|
| Branches permanentes | `main`, `juridica`, `inteligente` (ver [ESTRATEGIA-BRANCHES.md](../../ESTRATEGIA-BRANCHES.md)) |
| Branches temporárias | nenhuma; inventário e backup em bundle em [GIT-RECUPERACAO-INVENTARIO.md](../../GIT-RECUPERACAO-INVENTARIO.md) |
| PRs abertos | nenhum |
| Tag | `v1.0.4` no HEAD da `main` (commit registrado no relatório final da release e na própria tag) |

## Testes executados nesta release

| Suíte | Resultado |
|---|---|
| Backend `pytest` completo (banco novo, migrations até 0025) | 1219 passed, 3 skipped; mais 1 teste de política adicionado depois (`test_release_workflow_policy.py`: 23/23, 0 skipped no repositório com `.git`) |
| Pulados no backend | 2 testes reais do DataJud (API externa, opt-in `RUN_REAL_DATAJUD_TESTS=true`); 1 de bit de execução dos scripts, que pula sem `.git` na cópia temporária e roda no CI |
| Frontend | `tsc -b` 0 erros · `vitest` 29 arquivos / 182 testes · `vite build` OK |
| Docker | não há Docker na máquina de homologação; validado pelo job `Docker (compose + proxy + scripts + build prod)` do CI e pelo build das imagens no release |
| E2E Playwright (todas as specs, 8 viewports + release) | 196 passed, 7 skipped, 0 falhas (7,0 min), no código final, backend local sem chave |
| Pulados no E2E | 7 testes de `ia-real.spec.ts`: só rodam com `RADAR_E2E_OPENAI=1` e `RADAR_E2E_ALLOW_COST=SIM`; a IA real foi validada pelo caso-01 abaixo |
| Isolamento entre imóveis (sonda na API real) | 19/19 verificações OK: 401 sem token ou com token inválido; 404/422 ao ler, alterar ou apagar recurso do imóvel B pela rota do A; 422 ao citar evidência do B; listagem do A sem dados do B; dados do B intactos |
| Varredura de segredos | chave real ausente do histórico do Git (todas as refs), dos 600 arquivos versionados, de logs, `e2e/results`, `storage` e `backups`; `.env` nunca versionado. Único padrão `sk-` é o fixture falso de `tests/test_openai_hardening.py` |

### IA real: caso sintético `caso-01` (gpt-4o-mini, text-embedding-3-small)

| Item | Execução 1 | Execução 2 |
|---|---|---|
| Análise | concluída, 5/5 agentes | concluída, 5/5 agentes |
| Financeiro (custo total, resultado, preço máximo a 20%) | R$ 341.450 · −R$ 26.550 · R$ 136.266 (= gabarito) | idem |
| Veredito | DESFAVORÁVEL / NÃO ARREMATAR | idem |
| Fatos do gabarito com evidência (ponderado) | 11/20 | 15/20 |
| Citações válidas | 100% | 100% |
| Armadilhas de alucinação T1–T6 | 0 | 0 |
| Isolamento A × B | OK | OK |
| CPF em `llm_runs`/log | não | não |
| Custo registrado | US$ 0,0071 | US$ 0,0077 |

Bloqueio de orçamento (limites reduzidos, nunca aumentados): teto por análise de US$ 0,001 executou 2 agentes e bloqueou os outros 3 antes da chamada; teto mensal de US$ 0,005 bloqueou os 5 agentes sem nenhuma chamada ao provider.

A primeira execução desta homologação revelou dois defeitos, corrigidos antes da tag: HTTP 500 no detalhe do imóvel com chunks indexados (com exposição de texto bruto) e o agente checklist derrubado por `kind='pendente'`.

## Execução local

```bash
# backend (WSL/Linux), PostgreSQL 16 + pgvector em 127.0.0.1:54329
cd backend && alembic upgrade head
uvicorn app.main:app --host 127.0.0.1 --port 8100
# frontend
cd frontend && VITE_API_URL=http://127.0.0.1:8100 npx vite --host 127.0.0.1 --port 5180
# E2E (sem chave; nunca contra produção)
cd e2e && npx playwright test
# caso sintético com gabarito
python e2e/valor-negocio/valor_negocio.py --api http://127.0.0.1:8100 --db <dsn somente leitura> --log <log do backend>
```

## Configuração da IA

Variáveis no `.env` (nunca versionado; ver `.env.example`):

| Variável | Uso |
|---|---|
| `OPENAI_API_KEY` | chave do provider. Sem ela a análise roda só com as regras determinísticas e informa "IA indisponível" |
| `LLM_MODEL` / `EMBEDDING_MODEL` | `gpt-4o-mini` / `text-embedding-3-small` (1536 dimensões) |
| `LLM_BUDGET_USD_MONTH` | teto mensal; atingido, nenhuma chamada é feita |
| `LLM_BUDGET_USD_PER_ANALYSIS` | teto por análise; atingido, os agentes restantes não são chamados |
| `LLM_MAX_OUTPUT_TOKENS` | limite de saída por chamada |
| `LLM_REQUIRE_BUDGET=true` | sem os dois tetos, nenhuma chamada paga é feita |
| `LLM_REDACT_PII=true` | mascara CPF (com e sem pontuação), RG, telefone, e-mail e dados bancários antes de enviar ao provider e nos logs; pseudonimiza nomes de pessoas físicas **conhecidos** (cadastrados ou após rótulos como "Proprietário:"). Nomes citados livremente no texto não são detectados (sem NER) |

Modelo sem preço cadastrado é bloqueado antes da chamada (`tests/test_budget_pricing.py`).

## Deploy

O `release.yml` só faz deploy na VPS com a variável de repositório `DEPLOY_ENABLED=true`. Nesta release ela **não** foi definida: a tag valida, roda o CI e publica as imagens no GHCR, e a VPS continua na v1.0.3.

Antes de ligar o deploy: HTTPS válido e `REQUIRE_HTTPS=true` ([PLANO-HTTPS-VPS.md](PLANO-HTTPS-VPS.md)), backup do banco, limites de orçamento no `.env` da VPS, migrations até `0025` e o rollback abaixo testado.

## Rollback

- Código/imagens: voltar para a tag `v1.0.3` (`77ded35`), imagens `backend:v1.0.3` e `frontend:v1.0.3` no GHCR.
- Banco: `alembic downgrade 0024_analysis_version_unique` (remove só as colunas de origem/força da 0025; reversibilidade conferida no CI).
- VPS: `docs/GITHUB-ACTIONS-DEPLOY.md` §8.

## Uso com documentos reais

**Ainda não liberado.** Requisitos em [CRITERIOS-LIBERACAO-IMOVEL-REAL.md](CRITERIOS-LIBERACAO-IMOVEL-REAL.md). O bloqueio principal é a falta de HTTPS na VPS.

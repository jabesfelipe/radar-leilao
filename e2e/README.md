# E2E de homologação (Playwright)

Pasta isolada do produto: não altera `frontend/` nem `backend/`. Cobre a homologação da v1.0.2.

## Segurança

- Rode **somente** contra ambiente local/de teste. Os testes criam imóveis e documentos **fictícios**.
- Nunca aponte para produção. Nenhum teste lê, imprime ou grava a chave da OpenAI.
- `ia-real.spec.ts` consome crédito real e fica **desligado por padrão**.

## Pré-requisitos

1. Backend com PostgreSQL + pgvector, migrations aplicadas e um usuário ADMIN
   (ex.: `AUTH_BOOTSTRAP_ADMIN_EMAIL` / `AUTH_BOOTSTRAP_ADMIN_PASSWORD` no ambiente de teste).
2. Frontend em modo dev apontando para essa API (`VITE_API_URL`).
3. Google Chrome instalado (padrão `channel: chrome`) ou `npx playwright install chromium`
   com `RADAR_E2E_BROWSER_CHANNEL=` (vazio).

```powershell
cd e2e
npm install
$env:RADAR_E2E_FRONT_URL = "http://127.0.0.1:5180"
$env:RADAR_E2E_API_URL   = "http://127.0.0.1:8100"
$env:RADAR_E2E_EMAIL     = "admin-de-teste@local.test"
$env:RADAR_E2E_PASSWORD  = "<senha do ambiente de teste>"
npx playwright test mobile.spec.ts mobile-detalhe.spec.ts fluxo.spec.ts
```

## Suítes

| Arquivo | O que prova | Precisa de OpenAI? |
|---|---|---|
| `mobile.spec.ts` | 14 rotas + detalhe nos 7 viewports de `tests/helpers.ts` (360×800, 375×812, 390×844, 412×915, 430×932, 768×1024, 1366×768): overflow real (ignorando `overflow-x:hidden`), tabelas sem rolagem, fonte de input < 16px, login pela interface | Não |
| `mobile-detalhe.spec.ts` | As 18 seções do imóvel com dados semeados e o wizard de cadastro, nos 7 viewports | Não |
| `correcoes.spec.ts` | Status honesto da análise, estados de documento (API real) e layout corrigido nos 7 viewports | Não |
| `fluxo.spec.ts` | Cadastro → upload → processamento → análise sem chave → leitura mobile; verifica a transparência quando não há IA | Não |
| `ia-real.spec.ts` | Embeddings reais, `/analisar` com LLM, os 5 agentes, registro de tokens/custo | **Sim** (gated) |

Os testes de medição usam `expect.soft`: uma falha é um **achado** registrado, não um erro de infraestrutura.
Evidências ficam em `results/` (ignorado pelo Git): JSON por rota/viewport e screenshots.

## Executar a IA real (somente com autorização)

```powershell
$env:RADAR_E2E_OPENAI     = "1"     # o backend alvo tem chave configurada
$env:RADAR_E2E_ALLOW_COST = "SIM"   # autoriza consumo de crédito
npx playwright test ia-real.spec.ts
```

Para API remota, é preciso também `RADAR_E2E_ALLOW_REMOTE=SIM`. Ver
`docs/06-quality/homologacao-v1.0.2/PLANO-ATIVACAO-OPENAI.md` antes de executar.

> Testes com mocks não comprovam integração real. Somente `ia-real.spec.ts` rodando com chave válida comprova.

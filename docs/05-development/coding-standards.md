# Padrões de código

Apenas convenções **observadas no repositório**. Não há linter nem formatador configurados como obrigatórios no CI além de `tsc` (frontend) e `actionlint` (workflows).

## Gerais
- Experiência funcional em português do Brasil (telas, mensagens, documentação). Identificadores técnicos (classes, bibliotecas, APIs) podem ficar em inglês; nomes de domínio e chaves canônicas estão em português (ex.: `canonical_key = CONSOLIDACAO_REGISTRADA`).
- Dado ausente nunca vira zero: use `None` mais pendência e marque o resultado como provisório.
- Regra determinística fica em código (motores), não em LLM. A IA interpreta documentos e sempre cita evidência.
- Histórico é append-only: não sobrescreva versões, execuções, análises nem movimentações.
- Constantes eternas para tributos, emolumentos ou alíquotas são proibidas; use parâmetros com fonte e vigência.
- Chaves canônicas do checklist são imutáveis (inclusive com erro de grafia, como `COMPARAVEIS_SUFFICIENTES`).

## Backend (Python 3.12, FastAPI)
- Regras declarativas e versionadas em módulos de dados (`checklist.py`, `workflow_rules.py`, `modality_rules.py`, `legal_catalog.py`) e lógica pura separada (`workflow_engine.py`, `finance.py`).
- Novas rotas em `routers/` (modularização M0); rotas novas devem exigir autenticação (`get_current_user`, `authorized_writer` ou `require_permission`).
- Contrato OpenAPI protegido por baseline: atualize `tests/contract/openapi_baseline.json` quando a API mudar.
- Segredos nunca em logs, históricos, evidências nem prompts; credenciais de portais cifradas (Fernet).
- Configuração por variáveis de ambiente via `config.py` (pydantic-settings).

## Frontend (React 19, TypeScript)
- Sem react-router: o roteamento é manual em `App.tsx`; ao criar uma rota, atualize `App.tsx` e a sidebar.
- Chamadas à API somente por `frontend/src/services`; o token é injetado por `installAuthFetch` em `/api`.
- Interface em pt-BR; ícones com `lucide-react`.
- Build de produção com `VITE_API_URL` vazio.

## Scripts e infraestrutura
- Scripts `.sh` com modo 100755 (verificado por teste); `bootstrap-vps.sh` usa `set -euo pipefail`. Cuidado com pipes que encerram cedo sob `pipefail` (ver [infrastructure.md §6.1](../04-operations/infrastructure.md#61-troubleshooting-sshd--t-com-awk-no-passo-do-firewall)).
- Somente `ci.yml` e `release.yml` em `.github/workflows`.
- Na VPS use sempre `scripts/prod/compose.sh`.

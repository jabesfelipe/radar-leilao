# Radar Leilão — Controle Central do Projeto

> Documento operacional central do desenvolvimento.  
> Última consolidação: 21/09/2026  
> Branch principal: `main`  
> Repositório: `jabesfelipe/radar-leilao`

## 1. Objetivo

O Radar Leilão é um MVP local-first para análise rastreável de imóveis em **leilões extrajudiciais**, com imóvel como entidade central, documentos/evidências como fonte de verdade, análise incremental, histórico e memória estruturada.

A especificação arquitetural oficial permanece em:

- `SPEC-VIBE-CODING-RADAR-LEILAO.md`

Este documento controla o **andamento de implementação**, registra o que já foi validado e aponta a próxima tarefa.

---

## 2. Regra de desenvolvimento

Fluxo oficial:

1. Kiro lê este arquivo.
2. Kiro executa **somente a próxima TASK marcada como PENDENTE**.
3. Kiro implementa e cria commit.
4. Usuário informa: **"da pull"**.
5. O assistente consulta o GitHub, compara o commit com o último estado aprovado e revisa o código alterado.
6. Se houver problema, é criada correção antes de avançar.
7. Se estiver correto, a TASK recebe **[x] CONCLUÍDA** neste documento.
8. O próximo item pendente vira a próxima instrução operacional para o Kiro.
9. Cada avanço de tarefa deve deixar um commit rastreável.

### Critério de aprovação

Uma TASK só é considerada concluída quando:

- o código implementa o escopo solicitado;
- não inventa regra de negócio;
- não cria enum/regra/campo não suportado pela SPEC ou contrato existente;
- testes/build relevantes passam;
- não há regressão evidente;
- o escopo negativo da TASK foi respeitado;
- o commit é identificável.

---

## 3. Estado atual

**Último commit de implementação:** `23b47172f1855e7f6facde86142ed7762759615c`  
**Mensagem:** `fix: corrige serializacao decimal na integracao`

**Última TASK aprovada:** TASK 58

**TASK 59:** 🔵 EM EXECUÇÃO — correção da próxima falha real do fluxo de análise. Kiro está trabalhando nesta task.

**TASK 51:** execução diagnóstica realizada, não aprovada como E2E completo.

**TASK 51B:** runtime WSL + Docker + PostgreSQL/pgvector preparado; migrations corrigidas e validadas.

**TASK 52:** cadeia de migrations validada em banco limpo; 211 testes passaram e 10 falharam por problemas de aplicação fora do escopo da migration.

**TASK 53:** correção do snapshot anterior do Checklist aprovada.

**TASK 54:** concluída — fixture de `test_documents.py` corrigida; 213 passed, 8 failed.

**TASK 55:** concluída — fixture de `test_extraction.py` corrigida; 214 passed, 7 failed.

**TASK 56:** concluída — fixture de `test_extraction.py` corrigida; 215 passed, 6 failed.

**TASK 57:** concluída — fixture de `test_extraction.py` corrigida; 216 passed, 5 failed.

**TASK 58:** concluída — corrigido `db.refresh(result)` no endpoint `update_checklist`; 217 passed, 4 failed.

**Próxima falha:** fluxo de análise/persistência em `tests/test_integration_flows.py`.

**Status global:** 🟡 MVP em construção.

> A porcentagem de conclusão não é usada como fonte oficial. O controle por TASK abaixo é a referência.

---

# 4. Backlog controlado

As TASKs 01–50 permanecem concluídas conforme histórico abaixo e na documentação anterior.

## TASK 51 — Primeiro teste E2E com imóvel real da Caixa
- [~] EXECUÇÃO DIAGNÓSTICA REALIZADA — NÃO CONCLUÍDA
- Commit: `ea7db957b6ef6e739bfa19d086b4a508d462acc6`

## TASK 51B — Reexecução controlada do E2E após preparar runtime
- [x] CONCLUÍDA
- Runtime oficial WSL2 → Docker → PostgreSQL + pgvector validado.
- Migrations executadas e validadas em banco limpo.

## TASK 52 — Correção e validação da cadeia de migrations
- [x] CONCLUÍDA
- Commit de implementação: `b676a889fdfb79c4609b72107a345f9b5ed3a080`
- Validação em banco limpo: migrations 0001 → 0008.
- Resultado: 211 passed, 10 failed; falhas restantes eram de aplicação.

## TASK 53 — Corrigir snapshot anterior do Checklist
- [x] CONCLUÍDA
- Commit: `f36cecebb490112945d2f6a91ae96bf2e9492157`
- Auditoria: 🟢 aprovada.

## TASK 54 — Reexecutar suíte e corrigir a próxima falha
- [x] CONCLUÍDA
- Commit: `ecde86518d4d9d4136184877974f103b9735e80d`
- Resultado: 213 passed, 8 failed.

## TASK 55 — Corrigir a próxima falha da suíte
- [x] CONCLUÍDA
- Commit: `27a65e3cd21053d710c68338a4f1a853a4ad8caa`
- Resultado: 214 passed, 7 failed.

## TASK 56 — Corrigir a próxima falha da suíte
- [x] CONCLUÍDA
- Commit: `1aa3912445c3e25a6f0b9e2ac4fa93d9e82f1d74`
- Resultado: 215 passed, 6 failed.

## TASK 57 — Corrigir a próxima falha da suíte
- [x] CONCLUÍDA
- Commit: `4c26ee67243cc622b89748a607fc01e3e294ca26`
- Auditoria: 🟢 aprovada.
- Corrigida a fixture de `test_extraction.py` para fornecer `success=True`.
- Resultado: 216 passed, 5 failed.

## TASK 58 — Corrigir a próxima falha de integração
- [x] CONCLUÍDA
- Commit: `23b47172f1855e7f6facde86142ed7762759615c`
- Auditoria: 🟢 aprovada.
- Falha reproduzida inicialmente como `Decimal is not JSON serializable`, mas o traceback completo confirmou a causa real: o PATCH do Checklist retornava `{}`.
- Causa raiz: `update_checklist` fazia `db.commit(); return result` sem `db.refresh(result)`; após o commit, os atributos ORM expiravam e a serialização retornava objeto vazio.
- Correção: uma única linha em `main.py`, adicionando `db.refresh(result)` antes do retorno.
- Contrato preservado; não houve alteração de schema, migration, teste, regra de negócio ou conversão indevida para string.
- Resultado: teste alvo passou; `test_integration_flows.py`: 12 passed, 4 failed; suíte: 217 passed, 4 failed.

---

# 5. PRÓXIMA TASK — PENDENTE

## TASK 59 — Corrigir a próxima falha real do fluxo de análise
- [~] **EM EXECUÇÃO**
- Arquivo-alvo: `tests/test_integration_flows.py`
- Próxima falha:
  `test_execucao_analise_completa_atualiza_dossie`
- Contexto: existem 4 falhas restantes no fluxo de análise/persistência.
- Regra: reproduzir e confirmar a causa exata antes de alterar código.
- Corrigir **somente a primeira falha**.
- Se a correção fizer o teste alvo passar, executar a suíte de `test_integration_flows.py`, registrar o resultado e parar.
- Não corrigir as outras três falhas na mesma TASK.
- Não alterar migrations/schema sem evidência.
- Não mascarar a falha convertendo genericamente valores para string.
- Não alterar RAG/LLM/LangGraph/Risk/Verdict sem necessidade comprovada.

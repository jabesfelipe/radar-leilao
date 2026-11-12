# Fluxo de desenvolvimento

Processo independente de ferramenta. Qualquer pessoa (ou assistente de IA) que contribua segue as mesmas regras.
O texto antigo `DEVELOPMENT-WORKFLOW.md` era específico do Kiro e está arquivado em [../99-archive/originais](../99-archive/originais/DEVELOPMENT-WORKFLOW.md).

## Ciclo de uma mudança

1. **Entender**: leia o módulo em [../02-product/modules](../02-product/modules/) e a arquitetura em [../03-architecture](../03-architecture/README.md).
2. **Ambiente**: [getting-started.md](getting-started.md) (Docker Compose local).
3. **Implementar** em um branch a partir da `main`, com mudanças pequenas e incrementais.
4. **Testar**: [testing.md](testing.md). Backend e frontend precisam passar.
5. **Atualizar a documentação na mesma entrega** (regra obrigatória, ver abaixo).
6. **Pull request** para a `main`; o CI roda. Só então merge.
7. **Publicar** (quando fizer sentido): tag `vX.Y.Z` na `main`, que dispara o deploy ([../04-operations/github-actions.md](../04-operations/github-actions.md)).

## Regra de documentação na mesma entrega

Toda mudança que altere comportamento, API, dados, configuração, infraestrutura ou processo atualiza a documentação **no mesmo commit ou pull request**:

| Mudou... | Atualize |
|---|---|
| endpoint | módulo em `02-product/modules`, `tests/contract/openapi_baseline.json` e a contagem de paths citada em docs |
| tabela ou migration | [03-architecture/data-model.md](../03-architecture/data-model.md) |
| regra de negócio ou critério | `01-business/evaluation-criteria.md` ou `business-rules.md` |
| decisão de arquitetura | [03-architecture/decisions/README.md](../03-architecture/decisions/README.md) (novo ADR) |
| infra, workflow, scripts de `scripts/prod` | `04-operations/*` |
| módulo com novo status | [02-product/README.md](../02-product/README.md) |
| comentário de código que cita um documento | o caminho do documento (veja [99-archive](../99-archive/README.md)) |

Evite números voláteis (testes passando, quantidade de paths) em documentos de visão geral; quando for necessário, cite a fonte e a data.
Documento obsoleto vai para `docs/99-archive/` com `git mv` e uma linha na tabela do `99-archive/README.md`; não se apaga documento sem registrar conteúdo e destino.

## Migrations

Incrementais, com `downgrade()`, nunca editar uma migration já aplicada, backup e ensaio em banco descartável antes de aplicar em ambiente real. Ver [database-migrations.md](database-migrations.md).

## Regras de preservação

Nunca executar `DROP`, `TRUNCATE`, seeds ou limpezas destrutivas no banco com dados de referência (imóvel 633, V1 a V9, 45 `llm_runs`, 27 `canonical_key`, Central Jurídica). Nunca `docker compose down -v` como correção operacional.

## Git

- Commits pequenos e descritivos; documentação separada da mudança de código só quando for uma reestruturação puramente documental.
- Não force push na `main`. Tags `v*` são imutáveis e protegidas por ruleset.
- Nunca versionar `.env`, dumps, chaves ou tokens.

## Assistentes de IA (opcional)

O processo acima vale com ou sem IA. Instruções específicas de uma ferramenta (por exemplo, arquivos de steering do Kiro, `AGENTS.md`, `CLAUDE.md`) devem ficar em arquivos próprios da ferramenta, apontando para este documento, e não duplicar regras do projeto. Hoje o repositório **não tem** nenhum arquivo desse tipo; os prompts históricos usados com o Kiro estão em [../99-archive/prompts](../99-archive/prompts/).
Quem usa IA continua responsável por revisar o código gerado, rodar os testes e atualizar a documentação.

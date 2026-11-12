# GITHUB-ACTIONS-DEPLOY (movido)

> Este caminho é mantido apenas porque scripts e workflows do repositório (por exemplo
> `.github/workflows/release.yml`) citam seções deste arquivo em suas mensagens.
> O conteúdo foi consolidado em **[04-operations/github-actions.md](04-operations/github-actions.md)**.
> O texto original está preservado em
> [99-archive/originais/GITHUB-ACTIONS-DEPLOY.md](99-archive/originais/GITHUB-ACTIONS-DEPLOY.md).

## Mapa de seções

| Seção citada | Onde está agora |
|---|---|
| §1 O que acontece | [github-actions.md#1-fluxo-do-pipeline](04-operations/github-actions.md#1-fluxo-do-pipeline) |
| §2 Primeiro deploy × atualização | [github-actions.md#2-primeiro-deploy--atualização](04-operations/github-actions.md#2-primeiro-deploy--atualização) |
| §3 Configuração (secrets, variável, ruleset) | [github-actions.md#3-configuração-única](04-operations/github-actions.md#3-configuração-única) |
| §3.2 Secrets | [github-actions.md#32-secrets-e-variável](04-operations/github-actions.md#32-secrets-e-variável) |
| §4 Acompanhar | [github-actions.md#4-acompanhar-uma-execução](04-operations/github-actions.md#4-acompanhar-uma-execução) |
| §5 Rollback | [rollback em deployment.md](04-operations/deployment.md#4-rollback) |

## §8 Recuperação de falha

O workflow `release.yml` cita "§8" para recuperação de falha. Na versão original essa
recuperação estava numerada como §6 (a numeração citada pelo workflow nunca existiu como §8).
A tabela de recuperação por etapa (validate-tag, ci, publish, deploy) está em
[github-actions.md#8-recuperar-de-falha](04-operations/github-actions.md#8-recuperar-de-falha).

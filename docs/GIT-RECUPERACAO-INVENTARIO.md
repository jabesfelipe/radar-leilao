# Inventário de recuperação do Git

Data do levantamento: 2026-11-14. Base de comparação: `origin/main` em `77ded35` (tag `v1.0.3`).

## Backup feito antes de qualquer alteração

Pasta local, fora do repositório: `C:\Users\jabes.cun.ext\backup-git-recuperacao\20261114-124806\`

| Arquivo | Conteúdo |
|---|---|
| `radar-leilao-todas-refs.bundle` | bundle com todas as 22 refs (branches locais e remotas, tags, `refs/stash`), 19.665.357 bytes, verificado com `git bundle verify` ("The bundle records a complete history") |
| `refs-originais.txt` | `git show-ref` com o hash de cada ref antes da limpeza |
| `commits-todos.txt` | lista dos 396 commits alcançáveis por qualquer ref |
| `stash0.patch` | conteúdo do `stash@{0}` |

Para restaurar qualquer branch apagada: `git fetch <caminho>\radar-leilao-todas-refs.bundle "refs/remotes/origin/<nome>:refs/heads/<nome>"` (ou `refs/heads/<nome>` para as locais).

## Tags (não alteradas)

| Tag | Commit |
|---|---|
| `v1` | `bd38eec` |
| `v1.0.0` | `a87b354` |
| `v1.0.1` | `ea7e430` |
| `v1.0.2` | `8894096` (objeto de tag `ea2b510`) |
| `v1.0.3` | `77ded35` (objeto de tag `1c9e76b`) |

## Branches encontradas

"Exclusivos" = commits que não estão na `main`. "Conteúdo" = se as alterações já existem na `main` mesmo quando os commits não estão.

| Branch | Onde | HEAD | Exclusivos | Funcionalidade | Já na main? | Ação |
|---|---|---|---|---|---|---|
| `main` | local e remota | `77ded35` | — | linha principal (v1.0.3) | — | receber a v1.0.4 |
| `feat/v1.0.4-qualidade-ia-evidencias` | local e remota | `1f884c4` (+`eea2cde` viewport 1920x1080) | 8 | v1.0.4: orçamento LLM, function calling, citações, privacidade, comparação documental, selos no frontend, docs | não | merge normal (`--no-ff`) na main, depois apagar |
| `feat/v1.0.4-encoding-errado` | só local | `dbd5127` | 7 | mesma árvore de `1f884c4` (`git diff` vazio); só as mensagens de commit têm acentuação quebrada | sim (conteúdo idêntico) | apagar após o merge (`-D` justificado: conteúdo idêntico e no bundle) |
| `chore/organizar-artefatos-e2e` | local e remota | `abc3e49` | 0 | organização da pasta e2e (PR #4) | sim | apagar |
| `homologacao-v1.0.2` | local e remota | `7fa61bf` | 0 | homologação v1.0.2 | sim | apagar |
| `feature/security-hardening-openai` | local e remota | `e4a1bc7` | 0 | hardening OpenAI (PR #1) | sim | apagar |
| `feature/judicial-api` | só remota | `f861220` | 0 (214 atrás) | módulo jurídico: `judicial_api/`, `backend/app/judicial_client.py`, `judicial_integration.py`, `tests/judicial` | sim | vira a nova branch `juridica` (criada a partir da main) e é apagada |
| `feat/radar-leilao-intelligence-spec` | local e remota | `8a6eae9` (base `84c561f`) | 2 (`d896f48`, `8a6eae9`) | especificação `docs/03-architecture/specs/SPEC-RADAR-LEILAO-INTELLIGENCE.md` e índice no README de arquitetura | não | integrar na nova branch `inteligente`, depois apagar |
| `feat/radar-leilao-intelligence-spec-v2` | só remota | `dcf1e1f` (base `8894096`) | 2 (`6acc7b2`, `dcf1e1f`) | mesma SPEC (arquivo idêntico à v1); README partindo de uma main mais nova | não | integrar na `inteligente`, depois apagar |

### Stash

`stash@{0}` ("On feat/radar-leilao-intelligence-spec: !!GitHub_Desktop") contém só artefatos gerados em `e2e/results/` (screenshots e JSON). Esses arquivos não são versionados por decisão do projeto. O stash foi mantido como está e também está no bundle e em `stash0.patch`.

## Riscos identificados

- A README de arquitetura nas duas branches de especificação tem a linha da SPEC inserida antes do separador `|---|---|` da tabela, e a v1 tem `\n` literal. Ao integrar na `inteligente`, a tabela precisa ser corrigida.
- As duas branches de especificação têm commits diferentes com o mesmo conteúdo. Integrar as duas por merge evita perder qualquer commit e permite apagar ambas com `git branch -d`.
- Os workflows do GitHub Actions só disparam em `push`/`pull_request` para `main` (`ci.yml`) e em tags `v*.*.*` (`release.yml`). Nenhum workflow cita as branches temporárias, então apagá-las não afeta o CI. Criar uma tag dispara o release, por isso nenhuma tag é criada sem aprovação.
- A `feat/v1.0.4-encoding-errado` só pode ser apagada com `-D`, porque seus commits não são ancestrais da main. O conteúdo é idêntico e está no bundle.

## Recomendação aplicada

1. Merge normal (`git merge --no-ff`) da `feat/v1.0.4-qualidade-ia-evidencias` na `main`, sem squash, preservando os commits.
2. `juridica` criada a partir da main consolidada, pois todo o módulo jurídico já está na main.
3. `inteligente` criada a partir da main consolidada, com merge das duas branches de especificação e correção da tabela do README.
4. Exclusão das branches temporárias locais e remotas só depois de confirmar que cada commit exclusivo é ancestral de `main`, `juridica` ou `inteligente` (exceto a `encoding-errado`, de conteúdo idêntico).
5. Estado final esperado: só `main`, `juridica` e `inteligente`, locais e remotas, sincronizadas.

# Estratégia de branches

O repositório mantém três branches permanentes. Qualquer outra branch é temporária e deve ser apagada (local e remota) depois de integrada.

## Branches permanentes

| Branch | Papel | Origem | Quem recebe merge dela |
|---|---|---|---|
| `main` | linha de produção. Todo release (tag `vX.Y.Z`) sai daqui. CI roda em todo push e PR para `main`. | — | — |
| `juridica` | evolução do módulo jurídico (`judicial_api/`, `backend/app/judicial_client.py`, `backend/app/judicial_integration.py`, `tests/judicial`, `docs/03-architecture/specs/JUDICIAL-API-SPEC.md`). | criada da `main` em `e5967b2` (o conteúdo da antiga `feature/judicial-api` já estava na `main`) | `main`, por PR |
| `inteligente` | evolução do módulo Radar Leilão Intelligence (`docs/03-architecture/specs/SPEC-RADAR-LEILAO-INTELLIGENCE.md` e o código que vier dela). | criada da `main` em `e5967b2`, com merge das antigas `feat/radar-leilao-intelligence-spec` e `-v2` | `main`, por PR |

## Regras

1. **Nada vai direto para `main` sem validação.** Fluxo normal: branch de trabalho → PR para `main` → CI verde → merge.
2. **Merge, não squash, para trabalho com histórico relevante.** Use "Create a merge commit" no GitHub (ou `git merge --no-ff`). Squash só para branches de um único assunto, com commits de rascunho.
3. **Sem force push em `main`, `juridica` ou `inteligente`.** Se algo precisar ser desfeito, use `git revert`.
4. **Tags só em `main`, só com aprovação.** Criar uma tag `v*.*.*` dispara o `release.yml` (build e publicação de imagens). Tags existentes nunca são movidas nem apagadas.
5. **Manter `juridica` e `inteligente` atualizadas com a `main`.** Periodicamente: `git checkout juridica && git merge main && git push` (idem para `inteligente`). Isso evita divergência grande como a da antiga `feature/judicial-api`, que ficou 214 commits atrás.
6. **Branches temporárias** (`feat/...`, `fix/...`, `chore/...`, `docs/...`):
   - saem da branch permanente de destino (`main`, `juridica` ou `inteligente`);
   - vivem só até o merge;
   - são apagadas depois do merge com `git branch -d <nome>` e `git push origin --delete <nome>`;
   - nunca são apagadas com `-D` sem antes confirmar que os commits exclusivos estão preservados (`git log <destino>..<nome>` vazio, ou backup em bundle).
7. **Mensagens de commit em UTF-8.** No Windows, escreva a mensagem num arquivo UTF-8 e use `git commit -F arquivo`, para não repetir o problema de acentuação que gerou a antiga `feat/v1.0.4-encoding-errado`.
8. **Não versionar artefatos gerados.** `e2e/results/` é ignorado; não use stash para guardá-los.

## Como levar trabalho de `juridica` ou `inteligente` para a `main`

```bash
git checkout juridica
git merge main            # traz a main atual e resolve conflitos na branch de módulo
git push
# abrir PR juridica -> main no GitHub; aguardar CI verde; merge com "Create a merge commit"
```

Depois do merge, a branch de módulo continua existindo; não apague `juridica` nem `inteligente`.

## Antes de apagar qualquer branch

```bash
git fetch --all --prune
git log --oneline <destino>..<branch>        # precisa estar vazio
git merge-base --is-ancestor <branch> <destino> && echo preservada
```

Se houver dúvida, gere um backup antes: `git bundle create backup.bundle --all`.

## Histórico desta organização

A consolidação de 2026-11-14 está registrada em [GIT-RECUPERACAO-INVENTARIO.md](GIT-RECUPERACAO-INVENTARIO.md), com o backup em bundle e o destino de cada branch apagada.

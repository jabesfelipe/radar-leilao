# 04 — Operações

Infraestrutura, deploy, backup e operação do Radar Leilão na VPS Contabo.

| Documento | Conteúdo | Situação |
|---|---|---|
| [infrastructure.md](infrastructure.md) | **Documento central**: servidor, preparação, bootstrap, SSH, secrets, primeiro deploy, limitações | novo (consolida 4 docs) |
| [github-actions.md](github-actions.md) | CI e deploy por tag, recuperação de falha | novo |
| [deployment.md](deployment.md) | modelo de deploy, migrations em produção, rollback, TLS futuro | novo |
| [operations.md](operations.md) | monitoramento, troubleshooting, regras invioláveis | novo |
| [docker-deployment.md](docker-deployment.md) | o que roda dentro da VPS: serviços, cadeia de scripts, gate de schema, memória | válido (movido) |
| [backup-restore.md](backup-restore.md) | backup e restauração do banco e dos documentos | válido (movido) |
| [storage.md](storage.md) | storage local de documentos | válido (movido) |
| [homologation-guide.md](homologation-guide.md) | camadas de proteção do acesso restrito | atualizar (parcial) |
| [database-maintenance.md](database-maintenance.md) | limpeza e backup no ambiente local | atualizar (parcial) |

Caminho de leitura sugerido para quem vai operar: `infrastructure.md` → `github-actions.md` → `deployment.md` → `operations.md`.

Os scripts citam alguns caminhos antigos em mensagens; esses caminhos continuam existindo como stubs em `docs/`
(`GITHUB-ACTIONS-DEPLOY.md`, `BACKUP-RESTORE.md`, `DOCKER-DEPLOYMENT.md`, `infra/CONTABO-VPS.md`, `LOCAL-SETUP.md`).
Ver [99-archive](../99-archive/README.md).

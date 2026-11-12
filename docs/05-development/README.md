# 05 — Desenvolvimento

| Documento | Conteúdo | Situação |
|---|---|---|
| [getting-started.md](getting-started.md) | executar o projeto num notebook novo (Windows, WSL2, Docker Desktop), troubleshooting | válido (movido de `LOCAL-SETUP.md`) |
| [local-operations.md](local-operations.md) | operar o ambiente local (rebuild, logs, backup) | válido (movido de `OPERATIONS.md`) |
| [development-workflow.md](development-workflow.md) | ciclo de mudança, regra de documentação na mesma entrega, uso de IA | novo |
| [testing.md](testing.md) | como rodar testes, o que o CI executa | novo |
| [database-migrations.md](database-migrations.md) | procedimento seguro de migrations | válido (movido de `DATABASE-MIGRATION.md`) |
| [coding-standards.md](coding-standards.md) | convenções observadas no código | novo |

Ambiente local resumido (detalhes em `getting-started.md`): `./scripts/setup.sh` na primeira vez; `start.sh`, `stop.sh`, `restart.sh`, `health.sh`, `logs.sh`, `backup.sh`, `restore.sh`. `reset.sh` é **destrutivo** (apaga dados).
Portas de desenvolvimento: PostgreSQL 5432, backend 8000, Judicial API 8010, frontend 5173.

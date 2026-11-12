# Radar Leilão — Runbook de Operações

Procedimentos de operação e resposta a incidentes. Comandos assumem o compose de
produção (`scripts/prod/compose.sh ...`).

## 1. Saúde e diagnóstico

| O quê | Como |
|---|---|
| API viva | `GET /health` (via proxy) |
| Readiness (db + alembic) | `GET /api/monitoring/readiness` (autenticado) |
| RAG (cobertura/erros) | `GET /api/monitoring/rag` (autenticado) |
| Fila do worker | `GET /api/monitoring/rag/pending` (autenticado) |
| Storage (órfãos) | `GET /api/monitoring/storage` (admin) |
| Status dos containers | `docker compose ... ps` |
| Logs de um serviço | `docker compose ... logs -f backend` (ou worker/proxy/postgres) |

## 2. Indicadores mínimos a observar

- API/DB/worker ativos (containers healthy).
- Documentos em processamento / versões em erro (`/api/monitoring/rag`).
- Chunks sem embedding e cobertura % (`/api/monitoring/rag`).
- Espaço do banco (`docker exec radar-prod-postgres psql -c "SELECT pg_size_pretty(pg_database_size('radar_leilao'));"`).
- Espaço do storage (tamanho do volume `backend_storage`).
- Último backup (data do dump em `backups/` + `backup.log`).

## 3. Incidentes

### 3.1 Backend não sobe
1. `docker compose ... logs backend` — procurar stacktrace.
2. Checar `.env.prod`: `JWT_SECRET_KEY`/`POSTGRES_PASSWORD` definidos?
3. Postgres healthy? (`docker compose ... ps`). Readiness interna no entrypoint aguarda o DB.
4. Se for erro de schema, verificar `alembic current` vs head (não auto-migra em prod).

### 3.2 Banco indisponível
1. `docker compose ... logs postgres`. Volume `postgres_data` intacto?
2. Nunca recriar o volume sem backup. Restaurar de backup só em janela de manutenção
   (ver `docs/BACKUP-RESTORE.md`), nunca sobre o banco vivo sem backup atual.

### 3.3 Worker parado / fila crescendo
1. `docker compose ... logs worker`. `GET /api/monitoring/rag/pending` cresce?
2. Reiniciar: `docker compose ... restart worker`. Estado está no banco ⇒ retoma.
3. Disparo manual: `POST /api/monitoring/rag/reprocess` (admin).
4. Embeddings só são gerados com `OPENAI_API_KEY`; sem ela, ficam pendentes (esperado).

### 3.4 Perda de arquivos (storage)
1. Diagnóstico: `GET /api/monitoring/storage` (classifica órfãos; 633 sempre protegido).
2. Restaurar do backup do volume/S3. Reprocessamento é idempotente.
3. **Nunca** excluir diretórios automaticamente; `storage_governance.cleanup` é dry-run
   por padrão e exige confirmação explícita.

### 3.5 Recuperação de migrations
Ver `docs/DATABASE-MIGRATION.md` (backup → ensaio em banco descartável → aplicar →
conferir invariantes → rollback por `alembic downgrade` ou restore).

## 4. Desativação controlada do `X-Admin-Token` (legado)

O `X-Admin-Token` é um mecanismo de compat dos endpoints administrativos legados,
anterior ao RBAC real (Onda 11). Plano de desativação:
1. Confirmar que todos os consumidores administrativos usam JWT por papel (ADMIN).
2. Remover `ADMIN_API_TOKEN`/`AUTHZ_ROLE_TOKENS` do ambiente de produção (sem o token,
   o caminho de compat fica desabilitado — falha-fechada).
3. Validar que os fluxos admin continuam via JWT (testes de auth cobrem isso).
4. Em ciclo futuro, remover o código de compat após período de observação.
Não quebrar compat sem antes confirmar (passo 1) e ter os testes verdes.

## 5. Atualização de versão (deploy de nova release)
1. `git pull` na VPS.
2. Backup do banco (`scripts/prod/pg-backup.sh`).
3. `docker compose ... build` (novas imagens).
4. Migração controlada (`--profile migrate run --rm migrate`).
5. `docker compose ... up -d`.
6. Validação pós-deploy (ver `docs/PRODUCTION-CHECKLIST.md`).

## 6. Regras invioláveis
- Sem `docker compose down -v`, `DROP DATABASE/TABLE`, `TRUNCATE`, `VACUUM FULL` no vivo.
- Sem exclusão automática de documentos/chunks/diretórios.
- Preservar imóvel 633, V1–V9, 45 `llm_runs`, 27 `canonical_key`, Central Jurídica.

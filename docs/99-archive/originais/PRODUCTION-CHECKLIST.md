# Radar Leilão — Checklist de Produção

Checklist objetivo para considerar o Radar Leilão pronto para hospedagem. Marque cada
item antes de abrir ao público.

## Infraestrutura
- [ ] `docker-compose.prod.yml` sobe todos os serviços (`docker compose ps` → healthy).
- [ ] PostgreSQL **sem** porta publicada no host (confirmar em `docker compose config`).
- [ ] Proxy (nginx) é o único serviço com portas 80/443 expostas.
- [ ] Volumes persistentes criados (`postgres_data`, `backend_storage`).
- [ ] Logs limitados (json-file 10m x5) — já no compose.

## Configuração / segredos
- [ ] `.env.prod` criado a partir de `.env.prod.example` (NÃO versionado).
- [ ] `POSTGRES_PASSWORD` forte definido.
- [ ] `JWT_SECRET_KEY` forte definido (sem ele, login falha-fechada 503).
- [ ] `CORS_ALLOW_ORIGINS` = domínio público real (sem `*`).
- [ ] `VITE_API_URL=/api` (frontend atrás do proxy).
- [ ] (Opcional) `OPENAI_API_KEY` se quiser embeddings reais.
- [ ] (Opcional) `STORAGE_BACKEND=s3` + `STORAGE_S3_*` para desacoplar PDFs.

## Banco / migrations
- [ ] Backup criado e verificado ANTES de migrar (`scripts/prod/pg-backup.sh`).
- [ ] Migrations aplicadas pelo serviço `migrate` (não pelo start do backend).
- [ ] `alembic current` = head (`0023_usuarios`).
- [ ] Invariantes conferidos pós-migração (633=1, llm_runs=45, canonical_keys=27) se o
      banco já contiver o histórico.

## Segurança
- [ ] Containers rodam como usuário não-root (backend-prod uid 10001).
- [ ] HTTPS ativo (certificados válidos em `infra/certs/`; HSTS no proxy).
- [ ] RBAC validado (ADMIN/ANALISTA/OPERADOR/CONSULTA).
- [ ] `X-Admin-Token` legado: definir plano de desativação (ver OPERATIONS-RUNBOOK).
- [ ] Nenhum segredo em logs ou no bundle do frontend.

## Aplicação
- [ ] `GET /health` responde via proxy.
- [ ] `GET /api/monitoring/readiness` (autenticado) → db=true, alembic=head.
- [ ] Admin criado (bootstrap por env ou via `/api/auth/usuarios`).
- [ ] Worker em execução (processa embeddings pendentes).

## Observabilidade / operação
- [ ] `GET /api/monitoring/rag` acessível (cobertura de embeddings, versões em erro).
- [ ] Backup agendado (cron) em disco separado; retenção configurada.
- [ ] Restore ensaiado em banco descartável (`pg-restore-verify.sh`).
- [ ] Runbook de incidentes disponível (`docs/OPERATIONS-RUNBOOK.md`).

## Qualidade
- [ ] CI verde no último push (backend migrations+pytest; frontend tsc+vitest).
- [ ] Contrato OpenAPI sem regressão (143 paths no baseline).

## Bloqueios conhecidos (resolver antes de produção séria)
- [ ] Índice vetorial IVFFlat recriado após carga inicial (ou migrar p/ HNSW).
- [ ] Decidir backfill de embeddings ausentes (exige `OPENAI_API_KEY` + decisão).
- [ ] Storage de PDFs em S3/MinIO se o volume local não for aceitável para DR.

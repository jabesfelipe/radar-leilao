# Operação: monitoramento, incidentes e regras invioláveis

Procedimentos de operação em produção (VPS). Comandos assumem `DC=scripts/prod/compose.sh`, executado
em `/opt/radar-leilao`. Consolida o antigo `OPERATIONS-RUNBOOK.md` (§1 a §4 e §6; o §5, de deploy
manual, foi substituído por [deployment.md](deployment.md)).

## 1. Saúde e monitoramento

| O quê | Como |
|---|---|
| API viva | `GET /health` (via proxy, com o cookie do portão) |
| Readiness (banco + alembic) | `GET /api/monitoring/readiness` (autenticado) |
| RAG (cobertura, erros) | `GET /api/monitoring/rag` (autenticado) |
| Fila do worker | `GET /api/monitoring/rag/pending` (autenticado) |
| Storage (órfãos) | `GET /api/monitoring/storage` (admin) |
| Containers | `$DC ps` |
| Logs | `$DC logs -f --tail=100 backend` (também worker, proxy, postgres) |
| Recursos | `docker stats --no-stream`, `free -h`, `df -h`, `docker system df` |

Indicadores mínimos: containers saudáveis; documentos em processamento e versões em erro; chunks sem
embedding e cobertura percentual; tamanho do banco
(`docker exec radar-prod-postgres psql -U <usuario> -d <banco> -c "SELECT pg_size_pretty(pg_database_size(current_database()));"`);
tamanho do volume `backend_storage`; data do último backup em `/opt/radar-backups`.

Não há ferramenta de monitoramento externa nem alertas configurados (ver [limitações](../06-quality/known-limitations.md)).

## 2. Troubleshooting

### 2.1 Backend não sobe
1. `$DC logs backend` e procure o stacktrace.
2. Confirme que `.env.prod` tem `JWT_SECRET_KEY` e `POSTGRES_PASSWORD`.
3. PostgreSQL saudável? (`$DC ps`).
4. Mensagem `schema incompatível` = gate de schema: o banco não está na head do código. Não edite `alembic_version`; publique a versão por tag ou siga o procedimento em [deployment.md](deployment.md#3-migrations-em-produção).

### 2.2 Banco indisponível
1. `$DC logs postgres`; confirme que o volume `radar-prod_postgres_data` está intacto.
2. Nunca recriar o volume sem backup. Restauração só em janela de manutenção ([backup-restore.md](backup-restore.md)).

### 2.3 Worker parado ou fila crescendo
1. `$DC logs worker`; `GET /api/monitoring/rag/pending` cresce?
2. `$DC restart worker` (o estado fica no banco; retoma).
3. Disparo manual: `POST /api/monitoring/rag/reprocess` (admin).
4. Embeddings só são gerados com `OPENAI_API_KEY`; sem ela ficam pendentes (esperado hoje).

### 2.4 Perda de arquivos (storage)
1. Diagnóstico: `GET /api/monitoring/storage` (classifica órfãos; o imóvel 633 é sempre protegido).
2. Restaurar do backup do volume. O reprocessamento é idempotente.
3. Nunca excluir diretórios automaticamente; `storage_governance.cleanup` é dry-run por padrão e exige confirmação explícita. Ver [storage.md](storage.md).

### 2.5 Falha no bootstrap (firewall / `sshd -T`)
Ver [infrastructure.md §6.1](infrastructure.md#61-troubleshooting-sshd--t-com-awk-no-passo-do-firewall).

### 2.7 Respostas de erro da API (após o hardening de segurança)

| Código | Significado | O que fazer |
|---|---|---|
| 401 | sem login, token inválido/expirado ou usuário desativado | entrar novamente |
| 403 | papel sem permissão para a operação | pedir a um ADMIN o papel adequado |
| 409 | já existe análise/agente/extração igual em andamento | aguardar a conclusão; não repetir |
| 413 / 415 / 400 | arquivo grande demais (padrão 30 MB), MIME incompatível, vazio ou conteúdo que não corresponde à extensão | corrigir o arquivo |
| 429 | rate limit ou limite de operações simultâneas (`Retry-After` informa a espera) | aguardar; ajustar `RATE_LIMIT_*` só se houver necessidade real |
| 500 / 502 com `(ref: <id>)` | erro interno ou do provider | localizar o `<id>` nos logs: `scripts/prod/compose.sh logs backend | grep <id>` (detalhe técnico já sanitizado) |

Embedding que falhou: ver `extraction_metadata.embedding_last_error` da versão (categoria entre colchetes) e os logs do worker. Erros transitórios fazem backoff e não consomem as 5 tentativas.

### 2.6 Falha de deploy
Tabela por etapa em [github-actions.md §8](github-actions.md#8-recuperar-de-falha).

## 3. Desativação controlada do `X-Admin-Token` (legado)

`X-Admin-Token` é um mecanismo de compatibilidade dos endpoints administrativos, anterior ao RBAC por
JWT. Plano:

1. Confirmar que todos os consumidores administrativos usam JWT com papel ADMIN.
2. Remover `ADMIN_API_TOKEN` e `AUTHZ_ROLE_TOKENS` do ambiente de produção (sem o token, o caminho de compatibilidade fica desabilitado, falha-fechada).
3. Validar os fluxos administrativos via JWT (os testes de auth cobrem isso).
4. Em ciclo futuro, remover o código de compatibilidade após um período de observação.

Observação: a tela de Administração ainda exibe o campo "X-Admin-Token" (ver [módulo Administração](../02-product/modules/administration.md)).

## 4. Regras invioláveis

- Sem `docker compose down -v`, `DROP DATABASE/TABLE`, `TRUNCATE` nem `VACUUM FULL` no ambiente vivo.
- Sem exclusão automática de documentos, chunks ou diretórios.
- Preservar o imóvel 633 (COND PARQUE ARVOREDO RESIDENCIAL CLUBE), as análises V1–V9 e financeiras V1–V9, os 45 `llm_runs`, as 27 `canonical_key` e as 8 regras da Central Jurídica.
- Nunca versionar `.env`, chaves privadas, tokens nem a `GATE_KEY`.

## 5. Manutenção do banco

Ver [database-maintenance.md](database-maintenance.md) (atenção ao usuário do banco; o banner do arquivo registra a divergência).

# Radar Leilão — Procedimento de Migração de Banco (controlado)

Migrations usam **Alembic**. A cadeia atual vai de `0001_fundacao_radar` até
`0023_usuarios` (head). Em produção, migração é um procedimento **controlado** —
nunca um efeito colateral do start do backend.

> O backend de produção **não** aplica migrations ao subir (`RUN_MIGRATIONS_ON_START=false`).
> O serviço `migrate` (profile `migrate`) aplica sob demanda.

## 1. Entender a cadeia

```bash
# Listar a cadeia e a head do código:
scripts/prod/compose.sh --profile migrate \
  run --rm migrate sh -c "cd /app/backend && alembic history && alembic heads"
```

Nunca presuma que "basta `alembic upgrade head`": confirme a versão atual do banco vs. a
head do código antes de agir.

## 2. Procedimento obrigatório (ambiente real)

1. **Backup** do banco (formato custom):
   ```bash
   scripts/prod/pg-backup.sh backups
   ```
2. **Verificar o backup** (o próprio script valida via `pg_restore -l`; confira o log).
3. **Versão atual** do banco:
   ```bash
   scripts/prod/compose.sh --profile migrate \
     run --rm migrate sh -c "cd /app/backend && alembic current"
   ```
4. **Cadeia de migrations** conferida (passo 1) — sem ramos divergentes (um único head).
5. **Compatibilidade**: revisar o diff das migrations pendentes (código) antes de aplicar.
6. **Validar em banco descartável** (ensaio): restaure o backup num banco de teste e aplique
   a migração lá primeiro:
   ```bash
   scripts/prod/pg-restore-verify.sh backups/radar-radar_leilao-<STAMP>.dump radar_migr_rehearsal
   # (DROP_AFTER=false para inspecionar; depois aplique alembic upgrade head apontando a esse banco)
   ```
7. **Plano de rollback** definido ANTES (ver §3).
8. **Aplicar** no ambiente real — na VPS isso é feito pelo **deploy por tag** (backup →
   migrate → up; `docs/GITHUB-ACTIONS-DEPLOY.md`). Manual só em emergência:
   ```bash
   scripts/prod/compose.sh --profile migrate run --rm migrate
   ```
9. **Comparar dados críticos** antes/depois (preservação):
   ```sql
   SELECT (SELECT count(*) FROM properties WHERE id=633) prop633,
          (SELECT count(*) FROM llm_runs) llm_runs,
          (SELECT count(DISTINCT canonical_key) FROM checklist_items) ckeys;
   -- Esperado (invariantes históricos): 1, 45, 27.
   ```

## 3. Rollback

Alembic suporta downgrade quando a migration define `downgrade()` (as do Radar são
reversíveis e aditivas). Dois caminhos:

- **Downgrade Alembic** (preferido para 1 passo):
  ```bash
  scripts/prod/compose.sh --profile migrate \
    run --rm migrate sh -c "cd /app/backend && alembic downgrade -1"
  ```
- **Restore do backup** (quando o downgrade não é seguro / houve perda):
  ```bash
  # Restaure o dump custom num banco novo e aponte a aplicação para ele, OU
  # restaure sobre um banco recriado em janela de manutenção. NUNCA sobre o banco
  # vivo sem antes um backup atual. Use scripts/prod/pg-restore-verify.sh para ensaiar.
  ```

## 4. Estado conhecido (2026-11)

- Head do código: `0023_usuarios`.
- Em desenvolvimento, o banco `radar_leilao` já está em `0023` (confirmado por
  `alembic current`); código e banco **em sincronia**.
- As ondas 1/2 (Opportunity/Workflow/Modalidades) **não** criaram migration nova — reusam
  o schema de `0018`/`0019`. Próxima migration livre: **`0024`**.

## 5. Regras de preservação (inegociáveis)

- Nunca `DROP DATABASE/TABLE`, `TRUNCATE`, `VACUUM FULL` no banco vivo.
- Nunca backfill/seed destrutivo do histórico (imóvel 633, V1–V9, 45 `llm_runs`,
  27 `canonical_key`, Central Jurídica).
- Toda migração em ambiente real exige backup + ensaio em banco descartável + plano de
  rollback. Validar os invariantes (§2.9) antes de considerar concluída.

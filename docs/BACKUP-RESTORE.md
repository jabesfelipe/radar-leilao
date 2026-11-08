# Radar Leilão — Backup e Restauração

Estratégia de backup/restore para produção. Scripts em `scripts/prod/`. Testado
end-to-end em bancos descartáveis (ver §5).

## 1. O que precisa de backup

| Item | Como | Onde |
|---|---|---|
| Banco PostgreSQL | `pg_dump -Fc` (custom) | `scripts/prod/pg-backup.sh` |
| PDFs/documentos originais | volume `backend_storage` ou S3/MinIO | `scripts/backup.sh` (dev) / snapshot do volume / replicação S3 |
| Configuração sem secrets | versionado (`.env.prod.example`, compose) | repositório |

> O `.env.prod` (com segredos) **não** é versionado e **não** entra no backup de código.
> Guarde-o num cofre de segredos.

## 2. Backup do banco (produção)

```bash
scripts/prod/pg-backup.sh backups
```
- Formato custom (`-Fc`): compressão + restauração seletiva/paralela.
- Nome com data/hora: `radar-<db>-YYYYMMDD-HHMMSS.dump`.
- Verificação automática via `pg_restore -l`.
- Retenção: dumps mais antigos que `RETENTION_DAYS` (default 14) são **movidos** para
  `backups/archive/` — **nunca excluídos**.
- Log em `backups/backup.log`.

Agende via cron (ex.: diário 03:00) gravando em disco **separado** do banco:
```
0 3 * * * cd /opt/radar-leilao && RETENTION_DAYS=14 scripts/prod/pg-backup.sh /mnt/backups
```

## 3. Backup dos documentos

- **Local (volume):** snapshot do volume `backend_storage` (ex.: `docker run --rm -v
  radar-prod_backend_storage:/s -v /mnt/backups:/b alpine tar czf /b/storage-STAMP.tgz -C /s .`).
- **S3/MinIO:** use versionamento/replicação do bucket (recomendado em produção).
- Consistência banco×documentos: faça o backup do banco e do storage na mesma janela;
  como a ingestão é append-only e idempotente, pequenas defasagens são recuperáveis
  (reprocessamento não duplica).

## 4. Restauração

**Nunca** restaure sobre o banco vivo sem backup atual. Para ensaiar/validar:

```bash
scripts/prod/pg-restore-verify.sh backups/radar-radar_leilao-<STAMP>.dump radar_restore_check
```
- Restaura SEMPRE num banco **descartável** (recusa `radar_leilao`/`postgres`/`template*`).
- Valida estrutura (nº de tabelas), `alembic_version` e contagens básicas.
- Dropa o banco de verificação ao final (`DROP_AFTER=true`).

Restauração real (janela de manutenção): recrie o banco destino, restaure o dump com
`pg_restore` e aponte a aplicação. Documente no runbook de incidente.

## 5. Evidência de teste (2026-11)

Ciclo testado em bancos throwaway (nunca `radar_leilao`):
- Backup `-Fc` gerado e **verificado** (`pg_restore -l`).
- Restaurado em `radar_bkp_check`: estrutura + `alembic_version=0023_usuarios` +
  contagens conferidas; banco de verificação dropado ao fim.

## 6. Preservação

O backup é a rede de segurança dos invariantes históricos (imóvel 633, V1–V9, 45
`llm_runs`, 27 `canonical_key`, Central Jurídica). Sempre faça backup ANTES de qualquer
migração ou operação de manutenção (ver `docs/DATABASE-MIGRATION.md`).

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

## 3. Backup dos documentos (VPS)

```bash
scripts/prod/storage-backup.sh /opt/radar-backups
```
- Lê o volume `radar-prod_backend_storage` em modo **somente leitura**.
- Gera `storage-<STAMP>.tar.gz` (sem `tmp/`) + `storage-<STAMP>.sha256` (hash de cada
  arquivo, preservando estrutura e nomes) e verifica o `.tar.gz`.
- Consistência banco×documentos: rode `pg-backup.sh` e `storage-backup.sh` na mesma janela
  (o `deploy.sh update` já faz os dois). Ingestão é append-only, então uma defasagem curta
  só significa um arquivo novo sem metadado (ou vice-versa), detectável na validação (§4.3).

## 4. Restauração (sempre em destino isolado primeiro)

### 4.1 Banco
```bash
scripts/prod/pg-restore-verify.sh /opt/radar-backups/radar-radar_leilao-<STAMP>.dump radar_restore_check
```
Restaura num banco **descartável** (recusa `radar_leilao`/`postgres`/`template*`), valida
tabelas, `alembic_version` e contagens; `DROP_AFTER=false` mantém para inspeção.

### 4.2 Documentos
```bash
scripts/prod/storage-restore.sh /opt/radar-backups/storage-<STAMP>.tar.gz radar_restore_check_storage
```
- Recusa volumes em uso (`radar-prod_backend_storage`, `radar-leilao_backend_storage`) e
  qualquer volume **não vazio** — nunca sobrescreve.
- Pede confirmação digitada (`RESTAURAR`).
- Confere o hash de **cada** arquivo contra o manifesto (`sha256sum -c`).

### 4.3 Validar metadados × arquivos
Com banco e volume restaurados, confira que todo `document_versions.original_path` tem
arquivo correspondente:
```bash
scripts/prod/verify-restore-paths.sh radar_restore_check radar_restore_check_storage
# saída: paths=<n> faltando=<m>   (rc=1 se faltar algum arquivo)
```

### 4.4 Restauração real (desastre)
Em janela de manutenção, com backup atual do estado corrente:
1. `docker compose ... stop backend worker`
2. Restaure o dump num banco novo (`pg_restore -d <novo>`), valide (§4.1).
3. Restaure documentos num volume novo (§4.2), valide (§4.3).
4. Aponte o compose para o banco/volume novos (ou renomeie em manutenção) e suba.
Nunca use `down -v` nem restaure sobre o banco/volume em uso sem cópia.

## 5. Cópia fora da VPS (obrigatório)

Backup na mesma VPS não protege contra perda da VPS. Do seu computador:
```bash
rsync -avz radar@IP_DA_VPS:/opt/radar-backups/ ./radar-backups/
```
Ou um storage externo (Backblaze B2, outro servidor) via `rclone` — não contratado nesta fase.

## 6. Evidência de teste (2026-11)

Simulação local do compose de produção (projeto `radar-prod`, volumes isolados do dev):
- `pg-backup.sh`: dump custom de 272 KB, verificado com `pg_restore -l`.
- `pg-restore-verify.sh` em `radar_restore_check`: 69 tabelas, `alembic=0023_usuarios`,
  documentos/chunks/usuários com as mesmas contagens da origem.
- `storage-backup.sh`: 3 arquivos (original + normalizado + metadata), manifesto SHA-256.
- `storage-restore.sh` em volume novo: hashes de todos os arquivos conferidos; recusou o
  volume em uso (`rc=2`) e um volume não vazio (`rc=2`).
- `verify-restore-paths.sh`: todo caminho registrado no banco restaurado existe no volume
  restaurado.
Nada disso tocou `radar_leilao` (dev) — conferido por contagem antes/depois.

## 7. Preservação

O backup é a rede de segurança dos invariantes históricos (imóvel 633, V1–V9, 45
`llm_runs`, 27 `canonical_key`, Central Jurídica). Sempre faça backup ANTES de qualquer
migração ou operação de manutenção (ver `docs/DATABASE-MIGRATION.md`).

# Manutenção do banco local — Radar Leilão

## Limpeza de dados de teste

Script versionado em:

`scripts/db/cleanup_test_properties.sql`

Ele foi usado para limpar os imóveis de teste/resíduo do ambiente local, preservando exclusivamente o imóvel 633:

**COND PARQUE ARVOREDO RESIDENCIAL CLUBE**

### Garantias da limpeza

O script:

- exige que o imóvel 633 exista antes de iniciar;
- identifica todos os imóveis diferentes do 633;
- remove dependências antes dos registros de `properties`;
- preserva integralmente o imóvel 633;
- permite validação antes do `COMMIT`;
- deve ser executado dentro de uma transação.

Após a limpeza realizada em 02/10/2026, o ambiente de validação ficou com:

- 1 imóvel;
- imóvel 633 preservado;
- histórico V1–V9 preservado;
- sem V10 criada pela limpeza.

## Backup do banco

**Não versionar dumps do PostgreSQL no Git.**

O backup deve ficar fora do repositório, em local seguro, por exemplo:

`backups/radar-leilao/`

Sugestão de nome:

`radar_leilao_antes_limpeza_2026-10-02.sql`

### Gerar backup

Com Docker Compose:

```bash
docker compose exec postgres pg_dump -U postgres -d radar_leilao > backups/radar_leilao_$(date +%Y-%m-%d_%H%M%S).sql
```

No Windows/PowerShell, pode ser usado:

```powershell
docker compose exec postgres pg_dump -U postgres -d radar_leilao > "backups/radar_leilao_$(Get-Date -Format 'yyyy-MM-dd_HHmmss').sql"
```

### Restaurar

A restauração depende do ambiente e deve ser feita somente após confirmar o banco de destino:

```bash
psql -U postgres -d radar_leilao < backup.sql
```

**Atenção:** o dump pode conter dados sensíveis e deve ser mantido fora do GitHub.

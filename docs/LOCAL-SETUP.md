# Como executar o Radar Leilão em um notebook novo

Este guia é para quem **nunca usou Docker ou PostgreSQL**. Ao final, você terá o
Radar Leilão rodando localmente (banco, backend e frontend) com um único comando.

O ambiente oficial é **Windows + WSL2 + Docker**. Tudo roda em containers: você
**não** precisa instalar Python, Node, PostgreSQL nem criar banco manualmente.

---

## 1. O que você precisa instalar

| Ferramenta | Para que serve (em linguagem simples) |
|---|---|
| **Windows 10/11** | Sistema operacional. |
| **WSL2** | "Linux dentro do Windows". Os comandos rodam num Ubuntu. |
| **Ubuntu** | A distribuição Linux usada no WSL2. |
| **Docker Desktop** | Sobe o banco, o backend e o frontend em "caixinhas" isoladas (containers), sem instalar cada coisa na mão. |
| **Git** | Baixa o código do projeto. |

---

## 2. Instalar o WSL2

No **PowerShell como Administrador**:

```powershell
wsl --install
```

- Isso instala o WSL2 e o Ubuntu.
- **Reinicie o computador** quando pedir.
- Ao abrir o Ubuntu pela primeira vez, crie um **usuário e senha do Linux**.

Para confirmar:

```powershell
wsl -l -v
```

Você deve ver o `Ubuntu` com `VERSION 2`.

---

## 3. Instalar o Docker Desktop

1. Baixe o Docker Desktop em https://www.docker.com/products/docker-desktop/ e instale.
2. Abra o Docker Desktop → **Settings → Resources → WSL Integration** e **ative a integração com o Ubuntu**.
3. Deixe o Docker Desktop **aberto e "Running"**.

Para verificar (dentro do **Ubuntu/WSL**):

```bash
docker --version
docker compose version
```

Se ambos responderem uma versão, está pronto.

---

## 4. Baixar o projeto

Dentro do **Ubuntu/WSL**:

```bash
git clone https://github.com/jabesfelipe/radar-leilao.git
cd radar-leilao
```

---

## 5. Configurar o ambiente

Copie o arquivo de exemplo:

```bash
cp .env.example .env
```

- Você **não precisa alterar nada** para rodar localmente.
- O `.env` **não vai para o Git** (fica só no seu computador).
- **LLM é opcional:** deixe `OPENAI_API_KEY=` vazio. O projeto sobe sem chave;
  apenas as análises com IA ficam desativadas (o resto funciona normalmente).

---

## 6. Executar (setup automático)

```bash
./scripts/setup.sh
```

Esse comando:
1. verifica o Docker;
2. cria o `.env` se faltar;
3. sobe o banco, o backend e o frontend;
4. espera o banco ficar pronto e **aplica as migrations automaticamente**;
5. mostra as URLs no final.

> O **primeiro** `setup.sh` baixa imagens e faz build — pode levar alguns minutos.

---

## 7. Abrir o sistema

| O quê | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend  | http://localhost:8000 |
| Swagger (documentação da API) | http://localhost:8000/docs |

---

## 8. Parar (sem perder dados)

```bash
./scripts/stop.sh
```

Os dados do banco e dos documentos **ficam salvos** (em volumes do Docker).

---

## 9. Iniciar novamente

```bash
./scripts/start.sh
```

---

## 10. Verificar o ambiente

```bash
./scripts/health.sh
```

Mostra o estado de cada componente, por exemplo:

```text
PostgreSQL       OK
pgvector         OK
Migrations       OK
Backend          OK
Frontend         OK
```

---

## 11. Reiniciar

```bash
./scripts/restart.sh
```

Reinicia os containers **sem apagar dados**.

---

## 12. Resetar (APAGA os dados)

```bash
./scripts/reset.sh
```

⚠️ **Operação destrutiva.** Remove containers **e volumes**, ou seja:
- apaga o **banco PostgreSQL** (imóveis, análises, histórico);
- apaga os **arquivos de documentos** do storage.

O script **pede confirmação** antes de apagar. Faça um **backup antes** (passo 13).
Depois de resetar, rode `./scripts/setup.sh` para recriar tudo do zero.

---

## 13. Backup

```bash
./scripts/backup.sh
```

Gera uma pasta em `backups/radar-backup-AAAAMMDD-HHMMSS/` contendo:
- `postgres.sql.gz` — dump completo do banco;
- `storage.tar.gz` — arquivos de documentos (se existirem);
- `MANIFEST.txt` — descrição do backup.

**Não** inclui: `.env`, imagens Docker, código-fonte.

Você pode passar um destino: `./scripts/backup.sh /caminho/para/pasta`.

---

## 14. Restore (inclusive em outro notebook)

Copie a pasta de backup para o outro notebook (dentro do projeto), então:

```bash
./scripts/restore.sh backups/radar-backup-AAAAMMDD-HHMMSS
```

O restore:
- valida o arquivo de backup;
- **pede confirmação** (não sobrescreve em silêncio);
- restaura o banco;
- restaura os arquivos de documentos, quando houver;
- confere as migrations (`alembic upgrade head`).

Fluxo entre máquinas:

```text
Notebook A  →  backup.sh  →  pasta de backup  →  (copiar)  →  Notebook B  →  restore.sh
```

---

## Sobre armazenamento de documentos (MinIO)

O código **atual** guarda os documentos no **sistema de arquivos local**
(diretório `storage/documents`, dentro de um volume Docker persistente
`backend_storage`). O projeto **não usa MinIO/S3 hoje**, então o Docker Compose
**não sobe MinIO** — seria uma peça sem uso. Se, no futuro, o projeto passar a
usar MinIO de fato, ele poderá ser adicionado ao Compose neste mesmo padrão.

---

## Sobre a LLM (IA)

O Radar sobe **sem** `OPENAI_API_KEY`. Sem chave:
- banco, backend, frontend, migrations e testes determinísticos funcionam normalmente;
- as etapas que dependem de IA (extração/análise via LLM) ficam indisponíveis, sem quebrar o sistema.

Para habilitar IA, preencha `OPENAI_API_KEY` no `.env` e rode `./scripts/restart.sh`.

---

## 15. Troubleshooting (problemas comuns)

### Docker não está rodando
Abra o **Docker Desktop** e espere aparecer **"Running"**. Verifique:
```bash
docker info
```
Se der erro, o Engine não está ativo.

### Porta 5432 ocupada (PostgreSQL)
Algo já usa a porta do banco. Veja o que está na porta:
```bash
docker ps            # containers em execução
ss -ltnp | grep 5432 # quem escuta a porta (dentro do WSL)
```
Solução simples: pare o outro serviço, ou mude `POSTGRES_PORT` no `.env`.

### Porta 8000 ocupada (backend)
```bash
ss -ltnp | grep 8000
```
Mude `BACKEND_PORT` no `.env` e rode `./scripts/restart.sh`.

### Porta 5173 ocupada (frontend)
```bash
ss -ltnp | grep 5173
```
Mude `FRONTEND_PORT` no `.env` e rode `./scripts/restart.sh`.

### PostgreSQL não ficou saudável
```bash
docker compose logs postgres
```

### Backend não iniciou
```bash
docker compose logs backend
```
Causas comuns: banco ainda não pronto (o backend espera e tenta de novo) ou erro de migration (veja a próxima seção).

### Frontend não iniciou
```bash
docker compose logs frontend
```

### Migration falhou
Veja o log **sem apagar o banco**:
```bash
docker compose logs backend
```
Corrija a causa (geralmente aparece o erro do Alembic) e rode `./scripts/restart.sh`.
**Não** use `reset.sh` só por causa de migration — isso apagaria seus dados.

### Ambiente ficou inconsistente
Antes de qualquer coisa destrutiva:
1. gere um backup: `./scripts/backup.sh`;
2. veja os logs: `docker compose logs`;
3. tente `./scripts/restart.sh`.
Só use `./scripts/reset.sh` como último recurso (e depois de fazer backup).

---

## Comandos disponíveis (resumo)

| Comando | O que faz |
|---|---|
| `./scripts/setup.sh` | Prepara tudo do zero (notebook novo). |
| `./scripts/start.sh` | Inicia o ambiente já configurado. |
| `./scripts/stop.sh` | Para os containers, **preserva** os dados. |
| `./scripts/restart.sh` | Reinicia sem apagar dados. |
| `./scripts/health.sh` | Verifica a saúde dos componentes. |
| `./scripts/reset.sh` | **Apaga** dados (pede confirmação). |
| `./scripts/backup.sh` | Gera backup do banco + documentos. |
| `./scripts/restore.sh <pasta>` | Restaura um backup. |

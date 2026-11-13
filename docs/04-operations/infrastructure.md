# Infraestrutura — VPS Contabo do Radar Leilão

> Documento central de infraestrutura. Consolida o que antes estava espalhado em
> `infra/CONTABO-VPS.md`, `INFRASTRUCTURE-CONTABO.md`, `CONTABO-CHECKLIST.md` e `CAPACITY-PLANNING.md`
> (originais preservados em [99-archive/originais](../99-archive/originais/)).
>
> **Repositório público.** Este documento não registra IP, Customer ID, Order ID, senhas, chaves
> privadas, tokens nem o conteúdo de `.env`. O endereço do servidor aparece como `<VPS_HOST>`.
> Nenhum valor secreto foi reproduzido aqui; só os **nomes** dos secrets.

Legenda de evidência usada neste documento:

- **Observado**: resultado registrado em documentação anterior do repositório ou informado pelo proprietário.
- **Validado por teste local**: simulado em ambiente descartável, não na VPS real.
- **Pendente**: não há evidência no repositório.

## 1. Objetivo e escopo

Hospedar o MVP em uma única VPS com Docker Compose para testes funcionais remotos (celular, outro
computador). Não é uma arquitetura de produção endurecida (ver [§12](#12-segurança-e-limitações)).
Frontend, API, banco e worker rodam na mesma máquina; não há VPC nem múltiplas VMs.

## 2. Servidor contratado

| Item | Valor |
|---|---|
| Provedor / produto | Contabo, Cloud VPS 6 (2026) |
| Região | Hub Europe (latência a partir do Brasil ainda não medida, ver [pendências](#14-pendências)) |
| Sistema operacional | Ubuntu 24.04 LTS (24.04.5, codename `noble`) |
| Arquitetura / CPU | x86_64, 6 vCPU, AMD EPYC |
| Memória | ~11 GiB, mais **swap de 4 GiB** |
| Disco raiz | 192,69 GiB (~193 GB), ~191 GB livres no primeiro diagnóstico |
| Usuário inicial | `root` (usado só na preparação) |
| Usuário de deploy | `radar` (sem senha, grupo `docker`, chave SSH restrita) |
| Diretório da aplicação | `/opt/radar-leilao` |
| Diretório de backups | `/opt/radar-backups` (modo 700) |

Software validado na VPS (observado durante a preparação):

| Componente | Versão |
|---|---|
| Docker Engine | 29.9.3 |
| Docker Compose (plugin) | v5.7.1 |
| Docker Buildx | 0.38.1 |
| containerd.io | 2.4.2 |
| Kernel | 6.8.0-147 → **6.8.0-149-generic** após reboot |

## 3. Preparação da VPS (passos 1 a 10)

Executada uma vez, como `root`. Os passos 1 a 5 foram feitos manualmente; 6 a 10 são cobertos pelo
`scripts/prod/bootstrap-vps.sh` e pelo primeiro deploy.

1. **Diagnóstico inicial** do servidor (`lsb_release -a`, `nproc`, `free -h`, `df -h /`, `swapon --show`, `ip -br addr`, `docker --version`). Resultado: Ubuntu 24.04.5, 6 CPUs, 11 GiB, Docker e swap ausentes, kernel com atualização pendente.
2. **Instalação do Docker Engine** pelo repositório apt oficial ([§4](#4-instalação-do-docker-engine)).
3. **Swap de 4 GiB** ([§5](#5-swap)).
4. **Atualização de kernel e reboot**; depois do reboot, Docker e swap voltaram sozinhos.
5. **Validação pós-reboot**: `uname -r`, `systemctl status docker`, `free -h`, `swapon --show`.
6. **Bootstrap** (`bootstrap-vps.sh`): cria o usuário `radar`, autoriza a chave pública de deploy, cria `/opt/radar-leilao` e `/opt/radar-backups`, gera `.env.prod` ([§6](#6-bootstrap-do-servidor)).
7. **Firewall** (UFW): libera SSH e 80/tcp (`--configure-ufw`).
8. **Chave SSH de deploy** e `known_hosts` ([§7](#7-ssh-chaves-host-key-e-fingerprint)).
9. **Secrets e variável no GitHub** ([§8](#8-github-actions-secrets-variável-e-ruleset)).
10. **Primeira tag** (`v1.0.0`) e primeiro deploy automático ([§9](#9-primeiro-deploy-v100)).

## 4. Instalação do Docker Engine

Usa o repositório oficial do Docker para Ubuntu (como `root`).

```bash
apt update
apt install -y ca-certificates curl
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" \
  > /etc/apt/sources.list.d/docker.list

apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable docker && systemctl start docker
docker --version && docker compose version
docker run hello-world
```

Resultado observado: instalação concluída; `hello-world` executou com sucesso.

## 5. Swap

Margem para picos (builds, processamento de documentos).

```bash
fallocate -l 4G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
# antes de repetir, confira se a linha já existe em /etc/fstab (evita duplicidade)
echo '/swapfile none swap sw 0 0' >> /etc/fstab
free -h
```

Resultado observado: 4 GiB ativos, 0 B em uso logo após a criação, persistente no `/etc/fstab`.

## 6. Bootstrap do servidor

`scripts/prod/bootstrap-vps.sh` é idempotente e roda em 7 passos, como `root`:

```bash
git clone https://github.com/jabesfelipe/radar-leilao.git /root/radar-boot && cd /root/radar-boot
bash scripts/prod/bootstrap-vps.sh --deploy-pubkey "<LINHA_DA_CHAVE_PUBLICA>" --configure-ufw
```

Opções reconhecidas pelo script: `--deploy-pubkey`, `--configure-ufw`, `--public-ip`, `--admin-email`.

O que faz: cria o usuário `radar`; autoriza a chave **pública** com a opção `restrict`; cria
`/opt/radar-leilao` (clone) e `/opt/radar-backups`; gera `/opt/radar-leilao/.env.prod` com segredos
aleatórios (modo 600); imprime **uma única vez** a chave do portão (`GATE_KEY`) e a senha inicial do
administrador (guarde em gerenciador de senhas); mostra a impressão digital (fingerprint) da host key
do servidor; termina com a linha `BOOTSTRAP_OK`. Depois, apague o clone temporário
(`rm -rf /root/radar-boot`).

O usuário `radar` está no grupo `docker`, o que equivale a root na máquina. Use-o só para deploy.

### 6.1 Troubleshooting: `sshd -T` com `awk` no passo do firewall

**Sintoma.** O script para no passo "[6/7] Firewall", sem mensagem de erro e sem imprimir `BOOTSTRAP_OK`.

**Código antigo** (`scripts/prod/bootstrap-vps.sh`, linha 109 no commit `4691860`):

```bash
SSHP="$(sshd -T 2>/dev/null | awk '/^port /{print $2; exit}')"; SSHP="${SSHP:-22}"
```

**Causa.** O script usa `set -euo pipefail`. O `exit` do `awk` encerra a leitura assim que acha a
linha `port`; o `sshd -T` ainda escreve o restante da saída num pipe sem leitor e recebe SIGPIPE
(código 141). Com `pipefail`, a substituição de comando falha e `set -e` aborta o script, sem mensagem,
porque o stderr foi descartado (`2>/dev/null`). Reproduzido em teste local: com uma saída longa depois
da linha `port`, o pipeline antigo terminou com `rc=141` em 5 de 5 execuções. A causa foi confirmada
em laboratório (simulação com um `sshd` falso); no sshd real da VPS o diagnóstico é o mesmo, mas a
execução original não foi capturada.

**Correção no repositório.** `bootstrap-vps.sh` agora consome toda a saída do `sshd -T` e mantém o
padrão 22:

```bash
SSHP="$(sshd -T 2>/dev/null | awk '/^port / && !found {p=$2; found=1} END {if (found) print p}' || true)"
SSHP="${SSHP:-22}"
```

- O `awk` não usa `exit`: lê tudo, guarda a primeira linha `port` e imprime no `END`. Sem SIGPIPE.
- `|| true` faz o padrão 22 valer também se o `sshd -T` falhar ou não estiver no `PATH` (antes, isso também abortava o script sob `pipefail`).
- **22 é um fallback, não a confirmação da porta efetiva.** Se o `sshd -T` falhar ou não trouxer a linha `port`, o script assume 22 em silêncio e libera `22/tcp` no UFW. Num servidor com SSH em outra porta, confira com `sudo ss -tlnp | grep sshd` e ajuste a regra do UFW antes de fechar a sessão.
- Comportamento preservado: porta única, primeira porta quando há várias, 22 quando não há linha `port`.

A correção foi aplicada na VPS diretamente, antes de existir no repositório. O texto exato usado lá não
foi comparado com este; o resultado (bootstrap terminando com `BOOTSTRAP_OK`) foi informado pelo
proprietário. O bootstrap **não foi reexecutado** em produção após a mudança no repositório.

**Testes:** `tests/test_bootstrap_ssh_port.py` extrai a linha real do script e a executa com um `sshd`
falso (porta customizada com saída grande, várias portas, sem linha `port`, `sshd` falhando ou
ausente) e confere `bash -n`. Rodam no CI (job backend).

**Validação manual (como conferir o resultado).**

```bash
# a leitura da porta deve funcionar sem abortar mesmo com set -euo pipefail
bash -c 'set -euo pipefail; P="$(sshd -T 2>/dev/null | awk "/^port / && !found {p=\$2; found=1} END {if (found) print p}" || true)"; echo "porta=${P:-22}"'
# o bootstrap só está concluído se a saída terminar com BOOTSTRAP_OK
sudo ufw status verbose        # SSH e 80/tcp liberados
```

Regra geral de shell: sob `pipefail`, não encerre o leitor do pipe antes do fim (`exit`, `head -1`, `grep -q`) quando o escritor pode ter saída longa.

**Contorno manual do firewall**, se o script voltar a abortar nesse passo:

```bash
ufw allow OpenSSH      # ou: ufw allow <porta-ssh>/tcp
ufw allow 80/tcp
ufw --force enable
ufw status verbose
```

Com o script corrigido, esse contorno só é necessário se o `ufw` falhar por outro motivo.

## 7. SSH: chaves, host key e fingerprint

Quatro objetos diferentes, frequentemente confundidos:

| Objeto | O que é | Onde fica | Vai para o GitHub? |
|---|---|---|---|
| Chave **privada** de deploy (`radar_deploy`) | identidade do pipeline | só no seu computador e no secret | sim, como secret `VPS_SSH_KEY` |
| Chave **pública** de deploy (`radar_deploy.pub`) | autoriza a identidade | `~radar/.ssh/authorized_keys` na VPS (opção `restrict`) | não |
| **Host key** do servidor | identidade da VPS (`/etc/ssh/ssh_host_ed25519_key.pub`) | na VPS | sua linha pública vai em `VPS_KNOWN_HOSTS` |
| **Fingerprint SHA256** | resumo da host key para conferência humana | impresso pelo bootstrap | não (só conferir) |

Gerar a chave de deploy (no **seu computador**; a privada nunca vai para a VPS):

```bash
ssh-keygen -t ed25519 -f radar_deploy -N "" -C "radar-deploy"
```

Obter o `known_hosts` e conferir contra o fingerprint impresso pelo bootstrap:

```bash
ssh-keyscan -t ed25519 <VPS_HOST>                      # linha para o secret VPS_KNOWN_HOSTS
ssh-keyscan -t ed25519 <VPS_HOST> | ssh-keygen -lf -   # fingerprint SHA256 para comparar
```

`VPS_KNOWN_HOSTS` fixa a host key esperada: se alguém interceptar a conexão, o pipeline recusa. Sem
ele, o pipeline confia na host key vista no momento da conexão.

## 8. GitHub Actions: secrets, variável e ruleset

Secrets (Settings → Secrets and variables → Actions). Valores nunca devem aparecer em documentos ou logs.

| Secret | Conteúdo | Obrigatório |
|---|---|---|
| `VPS_HOST` | endereço da VPS | sim |
| `VPS_USER` | `radar` | sim |
| `VPS_APP_DIR` | `/opt/radar-leilao` | sim |
| `VPS_SSH_KEY` | chave privada de deploy | sim |
| `VPS_KNOWN_HOSTS` | linha da host key (`ssh-keyscan`) | recomendado |
| `VPS_PORT` | porta SSH (padrão 22) | não |
| `GHCR_USER` e `GHCR_TOKEN` | par opcional para ler pacotes | não |

Variável (não secreta): `VPS_PUBLIC_URL` (por exemplo `http://<VPS_HOST>`), que habilita o smoke externo.

**Ruleset de tags `v*`.** Ruleset de tag no GitHub com padrão `v*`, restringindo criação, atualização
e exclusão. Objetivo: tags imutáveis e deploy controlado, porque **a tag é a autorização do deploy**.
Uma tag recriada sobrescreveria as imagens daquele nome no GHCR; trate-as como imutáveis. Detalhes do
pipeline em [github-actions.md](github-actions.md).

## 9. Primeiro deploy (v1.0.0)

**Resultado observado (informado pelo proprietário; o repositório não guarda o log da execução):**

| Item | Registro |
|---|---|
| Versão | `v1.0.0` |
| Data | 12/11/2026 |
| Pipeline | concluído com sucesso |
| Tempo total | 5 minutos e 40 segundos |
| Build e publicação no GHCR | concluídos |
| Deploy na VPS | concluído |

**Distinção importante.** Documentos anteriores (`GITHUB-ACTIONS-DEPLOY.md` §7, `CONTABO-VPS.md` §6)
diziam que o pipeline "ainda não foi executado de verdade" e que bootstrap e secrets estavam
"pendentes". Isso era verdade **antes** do primeiro deploy e deixou de ser. O que continua sendo
**validado por teste local (simulação)**, e não observado na VPS: `rollback.sh`, a recusa quando o
schema diverge, a interrupção quando o backup falha, e o `bootstrap-vps.sh` em Ubuntu descartável.

Há também a tag `v1.0.1` (commit `ea7e430`), criada depois; seu deploy não está registrado neste
documento por falta de evidência. A tag `v1` é antiga e fora do padrão `vMAJOR.MINOR.PATCH`.

## 10. Operação

Comandos do dia a dia (na VPS, em `/opt/radar-leilao`):

```bash
scripts/prod/compose.sh ps                               # estado dos serviços
scripts/prod/compose.sh logs --tail=100 backend          # também: worker, proxy, postgres
grep RADAR_RELEASE_TAG .release.env                      # versão em execução
scripts/prod/post-deploy-check.sh                        # verificação pós-deploy
docker stats ; free -h ; swapon --show ; df -h ; docker system df
```

Sempre use `scripts/prod/compose.sh` (ele carrega o `.env.prod` e o `.release.env`), nunca
`docker compose` direto. Rotinas completas: [operations.md](operations.md), [deployment.md](deployment.md),
[backup-restore.md](backup-restore.md).

Após reboot da VPS: `uname -r`, `systemctl status docker --no-pager`, `free -h`, `swapon --show` e
`scripts/prod/compose.sh ps`. Não reinicie durante um deploy.

Dimensionamento (compose de produção): postgres 2 GB, backend 2 GB (`UVICORN_WORKERS=2`), worker 1 GB,
frontend 64 MB, proxy 64 MB, soma ≈ 5,1 GB dos ~11 GiB. A tabela antiga de 2 vCPU/4 GB
(`CAPACITY-PLANNING.md`) descrevia outro servidor e está arquivada.

### 10.1 Primeiro acesso depois do deploy

1. Em cada dispositivo, uma vez: `http://<VPS_HOST>/acesso?k=<GATE_KEY>` (cookie de 30 dias; sem ele tudo responde 403). A `GATE_KEY` foi impressa pelo bootstrap.
2. Abra `http://<VPS_HOST>` e entre com o administrador criado no bootstrap.
3. Remova a senha de bootstrap: apague o valor de `AUTH_BOOTSTRAP_ADMIN_PASSWORD` no `.env.prod` e rode `scripts/prod/compose.sh up -d --no-build backend`.
4. Crie os usuários de homologação (papel CONSULTA ou ANALISTA).
5. Valide: cadastrar imóvel de teste, enviar PDF/TXT, rodar análise (sem chave a IA responde `SEM_CHAVE`) e abrir financeiro, jurídico e due diligence.
6. Resumo esperado do smoke no primeiro deploy: modo `first`, `health=200`, `sem_cookie=403`, `interface_externa=200` e a versão em execução igual à tag.

### 10.2 Backups agendados (modelo, ainda não confirmado como instalado)

Cron do usuário `radar` (`crontab -e`), conforme o roteiro original. Horários: banco às 03:00, documentos às 03:20, limpeza de temporários às 04:30.

```bash
0 3 * * *  cd /opt/radar-leilao && RETENTION_DAYS=14 scripts/prod/pg-backup.sh /opt/radar-backups >> /opt/radar-backups/cron.log 2>&1
20 3 * * * cd /opt/radar-leilao && scripts/prod/storage-backup.sh /opt/radar-backups >> /opt/radar-backups/cron.log 2>&1
30 4 * * * cd /opt/radar-leilao && APPLY=true DAYS=1 scripts/prod/cleanup-temp.sh >> /opt/radar-backups/cron.log 2>&1
```

Todo deploy de **atualização** já faz backup antes de migrar, independentemente do cron. Cópia fora da VPS: [backup-restore.md](backup-restore.md).

### 10.3 Docker e firewall

O Docker publica portas com regras próprias no iptables e **ignora o UFW**. Com `PROXY_BIND=0.0.0.0` a porta 80 fica acessível mesmo sem regra no UFW; com `PROXY_BIND=127.0.0.1` (modo Tailscale) fica inacessível de fora mesmo com a regra. `PROXY_BIND=0.0.0.0` exige `ALLOW_PUBLIC_HTTP=1`.

Recomendação (manual): desligar o login por senha no SSH depois de confirmar que a chave funciona, testando um novo login antes de fechar a sessão atual.

```bash
printf 'PasswordAuthentication no\nPermitRootLogin prohibit-password\n' | sudo tee /etc/ssh/sshd_config.d/99-radar.conf
sudo sshd -t && sudo systemctl restart ssh
```

### 10.4 Reinicialização

Todos os serviços usam `restart: unless-stopped`: após `sudo reboot` tudo volta sozinho, com as imagens registradas em `.release.env`.

## 11. Estado atual validado

| Item | Estado | Fonte |
|---|---|---|
| Acesso SSH | validado | observado |
| Ubuntu 24.04, kernel 6.8.0-149 | ativo | observado (reboot realizado) |
| Docker 29.9.3, Compose v5.7.1 | ativo e habilitado no boot | observado |
| Swap 4 GiB | ativa e persistente | observado |
| Bootstrap e secrets | **concluídos** (deploy v1.0.0 depende deles) | informado pelo proprietário |
| Primeiro deploy v1.0.0 | sucesso, 5 min 40 s | informado pelo proprietário |
| Backups agendados e cópia externa | não confirmado | pendente |
| Teste pelo celular / outro computador | não registrado | pendente |

## 12. Segurança e limitações

- **HTTP sem TLS.** O acesso é por `http://<VPS_HOST>`. Tráfego, cookie do portão e token JWT trafegam sem criptografia. TLS exigiria um domínio e a configuração do proxy; não existe hoje.
- **Não usar dados sensíveis** (dados reais de pessoas, documentos confidenciais). Use dados sintéticos ou não sensíveis.
- **OCR desabilitado** (`OCR_ENABLED=false`): documentos digitalizados sem texto não são lidos.
- **`OPENAI_API_KEY` sem configuração**: sem chave, as análises de IA retornam `SEM_CHAVE` e os embeddings ficam pendentes (comportamento esperado).
- **Ambiente de testes (homologação)**, não produção endurecida.
- Camadas existentes: portão por cookie (`/acesso?k=`) no proxy, limite de 10 requisições por minuto no login, `/docs` retorna 404, UFW com SSH e 80/tcp, usuário de deploy restrito, PostgreSQL e backend sem portas públicas.
- Cuidados: nunca `docker compose down -v`; nunca `DROP`, `TRUNCATE` nem seeds destrutivos; confirme volumes e nome de projeto Compose (`radar-prod`) antes de limpar; nunca versione credenciais ou `.env`.
- Até o deploy do hardening de segurança, a produção tem endpoints legados sem autenticação no backend e o portão do proxy é a proteção de borda. A partir desse deploy, todas as rotas (exceto `/health` e o login) exigem JWT e permissão ([segurança](../03-architecture/security.md)); o portão do proxy permanece como camada adicional.

## 13. Referências

[github-actions.md](github-actions.md) · [deployment.md](deployment.md) · [backup-restore.md](backup-restore.md) ·
[storage.md](storage.md) · [homologation-guide.md](homologation-guide.md) · [docker-deployment.md](docker-deployment.md) ·
[operations.md](operations.md)

## 14. Pendências

1. ~~Registrar no repositório a correção do `sshd -T` + `awk`~~ feito em `bootstrap-vps.sh` (ver §6.1). Resta, opcionalmente, comparar com o texto aplicado na VPS e validar o script corrigido no próximo bootstrap de um servidor novo.
2. Anexar ao repositório (ou a documentação privada) a evidência do primeiro deploy (link da execução do Actions), já que data e tempo vêm da palavra do proprietário.
3. Configurar e documentar backups agendados e a cópia externa ao servidor.
4. Medir latência a partir do Brasil e consumo real (`docker stats`) durante o uso.
5. Definir domínio e TLS antes de qualquer uso além de teste.

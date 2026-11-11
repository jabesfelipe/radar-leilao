# Contabo — infraestrutura da VPS do Radar Leilão

> Documento operacional. Registra a contratação, o diagnóstico inicial e a preparação do servidor Contabo para hospedar o Radar Leilão.
>
> **Atenção:** este repositório é público. Por segurança, este documento não registra IP público, Customer ID, Order ID, senhas, chaves SSH ou outros identificadores de acesso. Mantenha esses dados em um cofre de senhas ou documentação privada. Nunca versione credenciais ou arquivos `.env`.

## 1. Objetivo

Hospedar inicialmente o MVP do Radar Leilão em uma única VPS, usando Docker Compose. A prioridade desta etapa é disponibilizar o produto remotamente para testes funcionais, validação do fluxo de negócio e testes de uso em diferentes dispositivos.

A arquitetura inicial concentra frontend, API, banco de dados e worker na mesma máquina. Não há VPC ou separação em múltiplas VMs nesta primeira implantação.

## 2. Dados da contratação e servidor

| Item | Informação |
|---|---|
| Provedor | Contabo |
| Produto | Cloud VPS 6 (2026) |
| Região informada | Hub Europe |
| Sistema operacional | Ubuntu 24.04.5 LTS |
| Arquitetura | x86_64 |
| CPU | 6 vCPU |
| Processador reportado | AMD EPYC Processor (with IBPB) |
| Memória RAM | aproximadamente 11 GiB |
| Disco raiz | 192,69 GiB (aprox. 193 GB) |
| Espaço livre no primeiro diagnóstico | aproximadamente 191 GB |
| Usuário administrativo inicial | root |

Os endereços IP e identificadores comerciais do pedido foram omitidos intencionalmente desta documentação pública.

## 3. Diagnóstico inicial

Diagnóstico executado após o primeiro acesso SSH:

- Ubuntu 24.04.5 LTS (codename `noble`).
- 6 CPUs online, identificadas como AMD EPYC.
- Memória: 11 GiB.
- Disco raiz: 193 GB, com aproximadamente 2,2 GB utilizados no primeiro diagnóstico.
- Interface de rede principal: `eth0`.
- Docker ainda não estava instalado.
- Swap ainda não estava configurada.
- O sistema indicou que havia uma atualização de kernel pendente.

### Comandos utilizados no diagnóstico

```bash
echo "===== SISTEMA ====="
lsb_release -a

echo "===== CPU ====="
nproc
lscpu | grep -E 'Model name|CPU\\(s\\)'

echo "===== MEMÓRIA ====="
free -h

echo "===== DISCO ====="
df -h /

echo "===== SWAP ====="
swapon --show

echo "===== REDE ====="
ip -br addr

echo "===== DOCKER ====="
docker --version 2>/dev/null || echo "Docker ainda não instalado"
```

## 4. Instalação do Docker Engine

Foi utilizado o repositório oficial do Docker para Ubuntu.

### 4.1. Atualizar índices e instalar dependências

```bash
apt update
apt install -y ca-certificates curl
```

### 4.2. Configurar chave e repositório oficial

```bash
install -m 0755 -d /etc/apt/keyrings

curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  -o /etc/apt/keyrings/docker.asc

chmod a+r /etc/apt/keyrings/docker.asc

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" \
  > /etc/apt/sources.list.d/docker.list

apt update
```

### 4.3. Instalar Docker Engine e plugins

```bash
apt install -y docker-ce docker-ce-cli containerd.io \
  docker-buildx-plugin docker-compose-plugin
```

### 4.4. Habilitar serviço e validar instalação

```bash
systemctl enable docker
systemctl start docker

docker --version
docker compose version

docker run hello-world
```

### 4.5. Resultado registrado

A instalação foi concluída com sucesso. Versões exibidas no terminal durante a instalação:

| Componente | Versão reportada |
|---|---|
| Docker Engine | 29.9.3 |
| Docker Compose | v5.7.1 |
| Docker Buildx | 0.38.1 |
| containerd.io | 2.4.2-3~ubuntu.24.04~noble |

O teste `docker run hello-world` foi executado com sucesso: a imagem foi baixada, o container foi criado e a mensagem **Hello from Docker!** foi exibida.

## 5. Configuração de Swap

Foi criada uma área de swap de 4 GiB para oferecer uma margem adicional em picos de consumo de memória, especialmente durante builds e processamento de documentos.

### Comandos executados

```bash
fallocate -l 4G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile

echo '/swapfile none swap sw 0 0' >> /etc/fstab

free -h
```

### Resultado registrado

- RAM total: aproximadamente 11 GiB.
- Swap configurada: 4 GiB.
- Swap utilizada imediatamente após a configuração: 0 B.
- Entrada adicionada ao `/etc/fstab` para ativação após reinicialização.

**Nota operacional:** antes de repetir o comando que adiciona a linha ao `/etc/fstab`, confira se a entrada já existe, para evitar duplicidade.

## 6. Estado atual conhecido

Validado após a reinicialização (informado em 11/11/2026):

| Item | Estado |
|---|---|
| Acesso SSH | Validado |
| Ubuntu 24.04.5 LTS | Instalado |
| Kernel ativo | `6.8.0-149-generic` (atualização aplicada; reboot realizado) |
| Docker Engine 29.9.3 / Compose 5.7.1 | Instalados; serviço ativo e habilitado na inicialização |
| Container de teste `hello-world` | Executado com sucesso |
| Swap de 4 GiB | Ativa e persistente no `/etc/fstab` |
| Bootstrap do deploy (`scripts/prod/bootstrap-vps.sh`) | **Pendente** |
| Secrets do GitHub Actions | **Pendentes** |
| Repositório / containers / PostgreSQL da aplicação | Ainda não implantados (o 1º deploy será a 1ª tag) |

## 7. Atualização de kernel — concluída

Durante a instalação do Docker o sistema indicou `Pending kernel upgrade` (de
`6.8.0-147-generic` para `6.8.0-149-generic`). A reinicialização foi realizada e o kernel
ativo é **`6.8.0-149-generic`**; Docker e swap voltaram sozinhos após o reboot.

Verificação de rotina após qualquer reboot futuro:

```bash
uname -r
systemctl status docker --no-pager
free -h
swapon --show
cd /opt/radar-leilao && scripts/prod/compose.sh ps     # depois do 1º deploy
```

Não reiniciar durante um deploy (acompanhe a aba Actions) ou processamento importante.

## 8. Arquitetura inicial planejada

A primeira implantação utilizará uma única VPS e Docker Compose:

- **Proxy / Nginx:** ponto de entrada HTTP/HTTPS e encaminhamento para frontend e API.
- **Frontend:** aplicação React.
- **Backend:** API FastAPI.
- **PostgreSQL + pgvector:** persistência relacional e vetorial.
- **Worker:** processamento assíncrono e tarefas em segundo plano.
- **Volumes Docker:** persistência de dados do banco e arquivos da aplicação.

O banco de dados e os serviços internos não devem precisar de portas públicas próprias. A exposição externa deve ocorrer pelo proxy, conforme a configuração de homologação do projeto.

## 9. Parâmetros de homologação desta fase

- Objetivo: testar o produto remotamente e evoluir funcionalidades.
- OCR: manter desligado inicialmente.
- Integrações pagas de LLM: não habilitar sem decisão explícita e configuração de chave.
- Dados: utilizar dados sintéticos ou não sensíveis durante os testes com HTTP público.
- Acesso: manter os mecanismos de acesso previstos no projeto; não publicar tokens, senhas ou chaves.
- VPC: não configurada nesta etapa; a aplicação começa em uma única VPS.
- Região: Hub Europe; medir latência a partir do Brasil durante os testes.

Esta configuração é de homologação/testes e não deve ser considerada, por si só, uma arquitetura de produção endurecida.

## 10. Cuidados operacionais

1. Nunca compartilhar ou versionar senha de root, chave privada SSH, tokens, chaves de API ou arquivos `.env`.
2. Não executar `docker compose down -v`: esse comando remove volumes e pode apagar dados persistentes.
3. Antes de atualizações de aplicação ou migrações, seguir os scripts e procedimentos de backup do próprio Radar Leilão.
4. Não executar reset, truncate, drop ou seeds destrutivos no banco.
5. Confirmar volumes, nomes de projeto Compose e diretórios de persistência antes de qualquer limpeza.
6. Manter backups do banco e dos documentos; configurar cópia externa ao servidor antes de depender da VPS como ambiente de uso contínuo.
7. Acompanhar RAM, swap, disco e logs durante testes de carga.

### Comandos úteis de operação

```bash
# Estado dos serviços Docker
systemctl status docker --no-pager

# Containers em execução
docker ps

# Containers e estado geral
docker compose ps

# Uso de CPU, memória e rede por container
docker stats

# Memória e swap
free -h
swapon --show

# Espaço em disco
df -h

# Uso do espaço por imagens, containers e volumes
docker system df
```

## 11. Próximas etapas

- [x] Concluir a atualização do kernel/reboot (`6.8.0-149-generic`).
- [x] Validar Docker e swap após reinicialização.
- [ ] Bootstrap único: `scripts/prod/bootstrap-vps.sh` (usuário de deploy `radar`, chave restrita,
      `/opt/radar-leilao`, `/opt/radar-backups`, `.env.prod` com segredos gerados na VPS, UFW SSH+80).
- [ ] Cadastrar as secrets do GitHub Actions (`docs/GITHUB-ACTIONS-DEPLOY.md §3.2`).
- [ ] Publicar a primeira tag (`v1.0.0`): primeiro deploy automático.
- [ ] Testar acesso pelo celular e por outro computador; validar persistência após reboot.
- [ ] Configurar backups agendados e cópia externa.
- [ ] Medir consumo (`docker stats`) e latência a partir do Brasil durante os testes.

Roteiro completo: `docs/CONTABO-CHECKLIST.md`.

---

**Última atualização:** 11/11/2026 (kernel/reboot validados; deploy automático por tag preparado)  
**Escopo:** contratação, diagnóstico e preparação da VPS Contabo. O deploy da aplicação é feito pelo GitHub Actions a partir da primeira tag.

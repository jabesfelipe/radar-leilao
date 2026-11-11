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

Com base na saída do terminal compartilhada em 11/11/2026:

| Item | Estado |
|---|---|
| Acesso SSH | Validado |
| Ubuntu 24.04.5 LTS | Instalado |
| Docker Engine | Instalado |
| Docker Compose plugin | Instalado |
| Docker habilitado na inicialização | Sim |
| Container de teste `hello-world` | Executado com sucesso |
| Swap de 4 GiB | Criada e ativada |
| Repositório Radar Leilão | Ainda não implantado nesta VPS |
| Containers da aplicação | Ainda não implantados nesta VPS |
| PostgreSQL da aplicação | Ainda não implantado nesta VPS |

## 7. Atualização de kernel pendente

Durante a instalação do Docker, o sistema informou:

- Kernel em execução: `6.8.0-147-generic`.
- Kernel esperado após atualização: `6.8.0-149-generic`.
- Mensagem: `Pending kernel upgrade` / `System restart required`.

A reinicialização **não foi executada** no procedimento registrado.

Antes do deploy da aplicação, planejar uma reinicialização controlada e validar o kernel ativo:

```bash
apt list --upgradable
uname -r
```

Se as atualizações continuarem pendentes, revisar os pacotes e aplicar a atualização em uma janela controlada. Após a atualização:

```bash
reboot
```

Depois de reconectar por SSH:

```bash
uname -r
systemctl status docker --no-pager
docker --version
docker compose version
free -h
df -h /
swapon --show
```

Não reiniciar durante uma implantação ou processamento importante. Até a validação pós-reboot, considerar a atualização de kernel como pendência.

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

- [ ] Planejar e concluir a atualização pendente do kernel/reboot.
- [ ] Validar Docker e swap após reinicialização.
- [ ] Preparar acesso SSH operacional sem depender do uso cotidiano de root.
- [ ] Revisar firewall e portas necessárias para a homologação.
- [ ] Clonar o repositório `radar-leilao` na VPS.
- [ ] Configurar o arquivo de ambiente de produção/homologação sem versionar segredos.
- [ ] Seguir o roteiro `scripts/prod/deploy.sh` e a documentação de homologação do projeto.
- [ ] Executar smoke tests e validar persistência.
- [ ] Testar acesso pelo celular e por outro computador.
- [ ] Medir consumo e latência durante os testes funcionais.

---

**Última atualização:** 11/11/2026  
**Escopo:** somente contratação, diagnóstico e preparação inicial da VPS Contabo. O deploy do Radar Leilão ainda é uma etapa posterior.

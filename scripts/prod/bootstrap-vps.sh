#!/usr/bin/env bash
# BOOTSTRAP ÚNICO da VPS (rode UMA vez, como root, depois que Docker/swap já estão instalados).
# Prepara tudo o que o deploy automático por tag assume que existe — e nada além disso:
#   - usuário operacional `radar` (sem senha, grupo docker) usado pelo GitHub Actions via SSH;
#   - chave pública do deploy autorizada para esse usuário (restrita: sem pty/forwarding);
#   - /opt/radar-leilao (clone do repositório) e /opt/radar-backups (700);
#   - .env.prod com segredos ALEATÓRIOS gerados aqui (só na VPS, chmod 600).
# NÃO sobe a aplicação: o primeiro deploy é a primeira tag (git push origin vX.Y.Z).
# Idempotente: nunca sobrescreve um .env.prod existente, nem remove nada.
#
#   sudo bash scripts/prod/bootstrap-vps.sh --deploy-pubkey "ssh-ed25519 AAAA... radar-deploy" \
#        [--public-ip 203.0.113.10] [--admin-email voce@exemplo.com] [--configure-ufw]
#
# Opções: --user (radar) --app-dir (/opt/radar-leilao) --backup-dir (/opt/radar-backups)
#         --repo-url (https://github.com/jabesfelipe/radar-leilao.git) --ref (main)
# (BOOTSTRAP_SKIP_DOCKER_CHECK=1 existe só para testar o script em contêiner descartável.)
set -euo pipefail

APP_USER="radar"; APP_DIR="/opt/radar-leilao"; BACKUP_DIR="/opt/radar-backups"
REPO_URL="https://github.com/jabesfelipe/radar-leilao.git"; REF="main"
PUBKEY="${DEPLOY_PUBKEY:-}"; PUBLIC_IP=""; ADMIN_EMAIL="admin@radar.local"; UFW=0
while [ $# -gt 0 ]; do
  case "$1" in
    --deploy-pubkey) PUBKEY="$2"; shift 2 ;;
    --public-ip) PUBLIC_IP="$2"; shift 2 ;;
    --admin-email) ADMIN_EMAIL="$2"; shift 2 ;;
    --user) APP_USER="$2"; shift 2 ;;
    --app-dir) APP_DIR="$2"; shift 2 ;;
    --backup-dir) BACKUP_DIR="$2"; shift 2 ;;
    --repo-url) REPO_URL="$2"; shift 2 ;;
    --ref) REF="$2"; shift 2 ;;
    --configure-ufw) UFW=1; shift ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "opção desconhecida: $1" >&2; exit 1 ;;
  esac
done

die() { echo "ERRO: $*" >&2; exit 1; }
[ "$(id -u)" -eq 0 ] || die "rode como root (sudo)."
printf '%s' "$APP_USER" | grep -Eq '^[a-z_][a-z0-9_-]{0,31}$' || die "--user inválido"
printf '%s' "$APP_DIR"  | grep -Eq '^/[A-Za-z0-9._/-]{1,100}$' || die "--app-dir inválido"
printf '%s' "$BACKUP_DIR" | grep -Eq '^/[A-Za-z0-9._/-]{1,100}$' || die "--backup-dir inválido"
printf '%s' "$ADMIN_EMAIL" | grep -Eq '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+$' || die "--admin-email inválido"
[ -n "$PUBKEY" ] || die "informe --deploy-pubkey com a chave PÚBLICA do deploy (gerada no seu computador)."
printf '%s' "$PUBKEY" | grep -Eq '^(ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp[0-9]+) [A-Za-z0-9+/=]+( .*)?$' || die "--deploy-pubkey não parece uma chave pública SSH (nunca envie a privada)."
printf '%s' "$PUBKEY" | grep -q 'PRIVATE' && die "isto é uma chave PRIVADA. Use o arquivo .pub."

echo "== [1/7] Pré-requisitos"
if [ "${BOOTSTRAP_SKIP_DOCKER_CHECK:-0}" != "1" ]; then
  command -v docker >/dev/null 2>&1 || die "Docker não encontrado (instale conforme docs/infra/CONTABO-VPS.md §4)."
  docker compose version >/dev/null 2>&1 || die "plugin docker compose ausente."
fi
need=""; for c in git openssl curl; do command -v "$c" >/dev/null 2>&1 || need="$need $c"; done
if [ -n "$need" ]; then apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq $need; fi

echo "== [2/7] Usuário operacional '$APP_USER'"
if id "$APP_USER" >/dev/null 2>&1; then echo "já existe"; else adduser --disabled-password --gecos "" "$APP_USER" >/dev/null; fi
if getent group docker >/dev/null 2>&1; then usermod -aG docker "$APP_USER"; fi

echo "== [3/7] Chave SSH do deploy (restrita)"
HOME_DIR="$(getent passwd "$APP_USER" | cut -d: -f6)"
install -d -m 700 -o "$APP_USER" -g "$APP_USER" "$HOME_DIR/.ssh"
AK="$HOME_DIR/.ssh/authorized_keys"; touch "$AK"; chmod 600 "$AK"; chown "$APP_USER:$APP_USER" "$AK"
KEYBODY="$(printf '%s' "$PUBKEY" | awk '{print $2}')"
if grep -qF "$KEYBODY" "$AK"; then echo "chave já autorizada"; else printf 'restrict %s\n' "$PUBKEY" >> "$AK"; echo "chave autorizada (restrict)"; fi

echo "== [4/7] Diretórios e clone"
install -d -m 755 -o "$APP_USER" -g "$APP_USER" "$APP_DIR"
install -d -m 700 -o "$APP_USER" -g "$APP_USER" "$BACKUP_DIR"
if [ -d "$APP_DIR/.git" ]; then
  echo "clone já existe em $APP_DIR (mantido)"
else
  [ -z "$(ls -A "$APP_DIR")" ] || die "$APP_DIR não está vazio e não é um clone git."
  runuser -u "$APP_USER" -- git clone --quiet "$REPO_URL" "$APP_DIR"
  runuser -u "$APP_USER" -- git -C "$APP_DIR" checkout --quiet "$REF"
fi
chmod +x "$APP_DIR"/scripts/prod/*.sh 2>/dev/null || true

echo "== [5/7] .env.prod"
ENVF="$APP_DIR/.env.prod"
if [ -f "$ENVF" ]; then
  echo ".env.prod já existe: NÃO foi alterado."
  GEN=0
else
  if [ -z "$PUBLIC_IP" ]; then
    PUBLIC_IP="$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src") {print $(i+1); exit}}')"
  fi
  printf '%s' "$PUBLIC_IP" | grep -Eq '^[0-9.]+$' || die "não consegui detectar o IP público; informe --public-ip."
  PGPW="$(openssl rand -hex 24)"
  JWT="$(openssl rand -base64 48 | tr -d '\n')"
  GATE="$(openssl rand -hex 24)"
  ADMIN_PW="$(openssl rand -base64 24 | tr -d '/+=\n' | cut -c1-24)"
  cp "$APP_DIR/.env.prod.example" "$ENVF"
  setkv() { sed -i "s|^$1=.*|$1=$2|" "$ENVF"; }
  setkv POSTGRES_PASSWORD "$PGPW"
  setkv JWT_SECRET_KEY "$JWT"
  setkv GATE_KEY "$GATE"
  setkv CORS_ALLOW_ORIGINS "http://$PUBLIC_IP"
  setkv AUTH_BOOTSTRAP_ADMIN_EMAIL "$ADMIN_EMAIL"
  setkv AUTH_BOOTSTRAP_ADMIN_PASSWORD "$ADMIN_PW"
  setkv BACKUP_DEST "$BACKUP_DIR"
  chown "$APP_USER:$APP_USER" "$ENVF"; chmod 600 "$ENVF"
  GEN=1
fi

echo "== [6/7] Firewall"
if [ "$UFW" = "1" ]; then
  command -v ufw >/dev/null 2>&1 || apt-get install -y -qq ufw
  SSHP="$(sshd -T 2>/dev/null | awk '/^port /{print $2; exit}')"; SSHP="${SSHP:-22}"
  ufw allow "$SSHP/tcp" >/dev/null; ufw allow 80/tcp >/dev/null; ufw --force enable >/dev/null
  echo "ufw: liberadas ${SSHP}/tcp (SSH) e 80/tcp. Obs.: o Docker publica a porta 80 por regra própria."
else
  echo "pulado (use --configure-ufw para liberar SSH+80 e ativar). Estado atual:"; ufw status 2>/dev/null | head -5 || echo "ufw ausente"
fi

echo "== [7/7] Verificação"
runuser -u "$APP_USER" -- docker info >/dev/null 2>&1 && echo "usuário $APP_USER acessa o Docker" || echo "AVISO: $APP_USER ainda não acessa o Docker (grupo vale no próximo login SSH)."
[ -f "$APP_DIR/scripts/prod/release.sh" ] || echo "AVISO: scripts/prod/release.sh não existe neste checkout ($REF). A primeira tag trará os scripts."
echo
echo "BOOTSTRAP_OK"
if [ "${GEN:-0}" = "1" ]; then
  cat <<EOF

============================================================================
GUARDE AGORA (aparece só esta vez; o resto fica em $ENVF, chmod 600):
  GATE_KEY (chave de entrada nos dispositivos): $GATE
  Admin do sistema: $ADMIN_EMAIL  /  senha: $ADMIN_PW
  1º acesso no navegador (depois do 1º deploy):
     http://$PUBLIC_IP/acesso?k=$GATE
  Depois do primeiro login: apague AUTH_BOOTSTRAP_ADMIN_PASSWORD do .env.prod.
============================================================================
EOF
fi
echo
echo "Impressão digital da host key (para a secret VPS_KNOWN_HOSTS, confira no seu PC):"
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub 2>/dev/null || true
echo "Próximos passos: cadastrar as secrets no GitHub e criar a primeira tag (docs/GITHUB-ACTIONS-DEPLOY.md)."

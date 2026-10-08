#!/bin/bash
# Native Apache installation for a dedicated Amazon Linux 2023 demonstration EC2.
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo 'Ejecute con sudo.'; exit 1; }
[[ $# -eq 2 ]] || { echo 'Uso: sudo bash scripts/install_apache_amazon_linux.sh IP_PUBLICA CORREO'; exit 1; }
source /etc/os-release
[[ $ID == amzn && $VERSION_ID == 2023 ]] || { echo 'Requiere Amazon Linux 2023.'; exit 1; }
REPO_DIR=$(cd "$(dirname "$0")/.." && pwd)
[[ $REPO_DIR != /opt/delegaciones/app ]] || { echo 'Ejecute desde su clon de trabajo, no desde /opt/delegaciones/app.'; exit 1; }
# Abort before modifying another website.
if compgen -G '/etc/httpd/conf.d/*.conf' >/dev/null; then
    if grep -l '^[[:space:]]*<VirtualHost' /etc/httpd/conf.d/*.conf /etc/httpd/conf/httpd.conf 2>/dev/null | grep -Ev '/(ssl|delegaciones)\.conf$'; then
        echo 'Hay otros sitios Apache. Revise su configuración antes de instalar.'; exit 1
    fi
fi
dnf install -y python3.12 python3.12-pip httpd mod_ssl postgresql17 postgresql17-server postgresql17-contrib rsync policycoreutils-python-utils
if [[ -f /etc/httpd/conf.d/ssl.conf ]]; then
    if rpm -V mod_ssl | grep -q '/etc/httpd/conf.d/ssl.conf'; then
        echo 'ssl.conf tiene modificaciones: revisar antes de reemplazar.'; exit 1
    fi
    mv /etc/httpd/conf.d/ssl.conf /etc/httpd/conf.d/ssl.conf.delegaciones-original
fi
id delegaciones >/dev/null 2>&1 || useradd --system --home-dir /var/lib/delegaciones --shell /sbin/nologin delegaciones
install -d -m 0755 /opt/delegaciones/app
rsync -a --delete --exclude=.git --exclude=.local --exclude=.venv --exclude=vendor/wheels --exclude=dist --exclude=staticfiles --exclude=__pycache__ --exclude='*.pyc' --exclude='.env*' --exclude='*.key' --exclude='*.pem' --exclude='*.crt' --exclude='*.sqlite3' --exclude='*.dump' "$REPO_DIR/" /opt/delegaciones/app/
chown -R root:root /opt/delegaciones/app
python3.12 -m venv /opt/delegaciones/venv
/opt/delegaciones/venv/bin/pip install --require-hashes -r /opt/delegaciones/app/requirements-prod.lock
python3.12 -m venv /opt/delegaciones/certbot
/opt/delegaciones/certbot/bin/pip install --require-hashes -r /opt/delegaciones/app/requirements-certbot.lock
install -d -o root -g delegaciones -m 0750 /etc/delegaciones
install -d -o delegaciones -g delegaciones -m 0700 /var/lib/delegaciones
install -d -o delegaciones -g apache -m 0755 /var/www/delegaciones-static
install -d -m 0755 /var/www/delegaciones-acme/.well-known/acme-challenge
CONFIG_EXTRA=()
[[ ! -f /etc/letsencrypt/live/municipal-ip/fullchain.pem ]] || CONFIG_EXTRA=(--https)
python3.12 /opt/delegaciones/app/scripts/apache_config.py "$1" "$2" "${CONFIG_EXTRA[@]}"
chown delegaciones:delegaciones /etc/delegaciones/config.json
[[ -f /var/lib/pgsql/data/PG_VERSION ]] || postgresql-setup --initdb
# Add a narrow password-authentication rule before distribution defaults.
python3.12 - <<'PY'
from pathlib import Path
p = Path('/var/lib/pgsql/data/pg_hba.conf')
s = p.read_text()
rule = 'host delegaciones delegaciones 127.0.0.1/32 scram-sha-256'
if rule not in s.splitlines():
    p.write_text(rule + '\n' + s)
PY
systemctl enable --now postgresql
systemctl reload postgresql
if [[ $(runuser -u postgres -- psql -At -c 'SHOW listen_addresses') != localhost ]]; then
    echo 'PostgreSQL no está limitado a localhost. Revise antes de continuar.'; exit 1
fi
cat /etc/delegaciones/config.json | runuser -u postgres -- /opt/delegaciones/venv/bin/python /opt/delegaciones/app/scripts/provision_apache.py
# SELinux maps /run to /var/run; register the canonical policy path.
semanage fcontext -a -t httpd_var_run_t '/var/run/delegaciones(/.*)?' 2>/dev/null || semanage fcontext -m -t httpd_var_run_t '/var/run/delegaciones(/.*)?'
restorecon -R /var/www/delegaciones-static /var/www/delegaciones-acme
install -m 0644 /opt/delegaciones/app/deploy/apache/*.service /opt/delegaciones/app/deploy/apache/*.timer /etc/systemd/system/
cat > /usr/local/bin/municipal-manage <<'MANAGE'
#!/bin/bash
set -euo pipefail
cd /opt/delegaciones/app
exec runuser -u delegaciones -- env DJANGO_CONFIG_FILE=/etc/delegaciones/config.json DJANGO_DEMO_CREDENTIALS_FILE=/var/lib/delegaciones/demo-credentials.json /opt/delegaciones/venv/bin/python manage.py "$@"
MANAGE
chmod 0755 /usr/local/bin/municipal-manage
municipal-manage migrate --noinput
municipal-manage collectstatic --noinput
municipal-manage check --deploy --fail-level WARNING
runuser -u delegaciones -- env DJANGO_CONFIG_FILE=/etc/delegaciones/config.json DJANGO_DEMO_CREDENTIALS_FILE=/var/lib/delegaciones/demo-credentials.json /opt/delegaciones/venv/bin/python /opt/delegaciones/app/scripts/demo.py
httpd -t
systemctl daemon-reload
systemctl enable delegaciones httpd
systemctl restart delegaciones httpd
echo 'Instalación preparada. Continúe con HTTPS en docs/apache-paso-a-paso.md.'

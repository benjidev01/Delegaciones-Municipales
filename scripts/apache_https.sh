#!/bin/bash
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo 'Ejecute con sudo.'; exit 1; }
ACTION=${1:-status}
APP_DIR=/opt/delegaciones/app
PUBLIC_IP=$(python3.12 -c "import json; print(json.load(open('/etc/delegaciones/public.json'))['ip'])")
CONTACT_EMAIL=$(python3.12 -c "import json; print(json.load(open('/etc/delegaciones/public.json'))['email'])")
case "$ACTION" in
  test|issue)
    CERT_NAME=municipal-ip
    EXTRA=()
    if [[ $ACTION == test ]]; then CERT_NAME=municipal-ip-staging; EXTRA=(--staging); fi
    /opt/delegaciones/certbot/bin/certbot certonly --webroot -w /var/www/delegaciones-acme --ip-address "$PUBLIC_IP" --required-profile shortlived --cert-name "$CERT_NAME" --email "$CONTACT_EMAIL" --agree-tos --non-interactive "${EXTRA[@]}"
    ;;
  activate)
    [[ -f /etc/letsencrypt/live/municipal-ip/fullchain.pem ]] || { echo 'Falta emitir certificado de producción.'; exit 1; }
    cp /etc/httpd/conf.d/delegaciones.conf /etc/httpd/conf.d/delegaciones.conf.previous
    python3.12 "$APP_DIR/scripts/apache_config.py" "$PUBLIC_IP" "$CONTACT_EMAIL" --https
    if ! httpd -t; then
        mv /etc/httpd/conf.d/delegaciones.conf.previous /etc/httpd/conf.d/delegaciones.conf
        echo 'Se restauró la configuración anterior.'; exit 1
    fi
    systemctl reload httpd
    # Remove the staging renewal job; retain the certificate for diagnosis.
    if [[ -f /etc/letsencrypt/renewal/municipal-ip-staging.conf ]]; then
        mv /etc/letsencrypt/renewal/municipal-ip-staging.conf /etc/letsencrypt/renewal/municipal-ip-staging.conf.disabled
    fi
    systemctl enable --now delegaciones-renew.timer
    ;;
  renew-test)
    /opt/delegaciones/certbot/bin/certbot renew --cert-name municipal-ip --dry-run
    ;;
  status)
    systemctl --no-pager status httpd delegaciones delegaciones-renew.timer
    ;;
  *) echo 'Use test, issue, activate, renew-test o status.'; exit 1 ;;
esac

#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
test -f .local/ec2.env || { echo 'Ejecute primero scripts/prepare_ec2.py.' >&2; exit 1; }
dc() { docker compose --env-file .local/ec2.env -f compose.ec2.yaml "$@"; }
case "${1:-help}" in
  bootstrap)
    python3 scripts/render_ec2.py http
    dc up -d proxy
    ;;
  cert-test|cert-issue)
    public_ip=$(python3 scripts/ec2_config.py ip)
    acme_email=$(python3 scripts/ec2_config.py email)
    if [ "$1" = cert-test ]; then
      dc run --rm certbot certonly --webroot -w /var/www/acme \
        --ip-address "$public_ip" --cert-name municipal-ip-staging \
        --required-profile shortlived --preferred-challenges http \
        --email "$acme_email" --agree-tos --non-interactive --test-cert
    else
      dc run --rm certbot certonly --webroot -w /var/www/acme \
        --ip-address "$public_ip" --cert-name municipal-ip \
        --required-profile shortlived --preferred-challenges http \
        --email "$acme_email" --agree-tos --non-interactive
    fi
    ;;
  activate)
    dc run --rm --entrypoint sh certbot -c \
      'test -s /etc/letsencrypt/live/municipal-ip/fullchain.pem && test -s /etc/letsencrypt/live/municipal-ip/privkey.pem'
    dc up --build --wait -d web
    python3 scripts/render_ec2.py https
    if ! dc run --rm --no-deps proxy -t; then
      python3 scripts/render_ec2.py http
      echo 'Nginx rechazó la configuración HTTPS; se restauró el archivo HTTP de preparación.' >&2
      exit 1
    fi
    dc up -d proxy
    dc exec -T proxy nginx -s reload
    ;;
  renew)
    dc run --rm certbot renew --cert-name municipal-ip --non-interactive --quiet
    dc exec -T proxy nginx -t
    dc exec -T proxy nginx -s reload
    ;;
  status)
    dc ps -a
    ;;
  down)
    dc down
    ;;
  *)
    echo 'Uso: sh scripts/ec2.sh bootstrap|cert-test|cert-issue|activate|renew|status|down'
    exit 1
    ;;
esac

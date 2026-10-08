#!/bin/bash
# Apply this visual release to the existing native Apache installation.
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo 'Ejecute con sudo.'; exit 1; }
REPO_DIR=$(cd "$(dirname "$0")/.." && pwd)
APP_DIR=/opt/delegaciones/app
[[ -f "$APP_DIR/manage.py" && -f /etc/delegaciones/config.json ]] || { echo 'Falta la instalación nativa Apache.'; exit 1; }
[[ $REPO_DIR != "$APP_DIR" ]] || { echo 'Ejecute desde el clon de trabajo.'; exit 1; }
command -v municipal-manage >/dev/null || { echo 'Falta municipal-manage; complete el instalador Apache.'; exit 1; }
[[ -f "$REPO_DIR/static/civica-logo.png" && -f "$REPO_DIR/templates/admin/base_site.html" ]] || { echo 'Actualice el clon completo antes de continuar.'; exit 1; }
# Back up interface files only; private configuration stays in /etc/delegaciones.
BACKUP_DIR=/var/backups/delegaciones-diseno
install -d -m 0700 "$BACKUP_DIR"
BACKUP_FILE="$BACKUP_DIR/interfaz-$(date -u +%Y%m%dT%H%M%SZ)-$$.tar.gz"
umask 077
tar -czf "$BACKUP_FILE" -C "$APP_DIR" templates static
rsync -a --chown=root:root "$REPO_DIR/templates/" "$APP_DIR/templates/"
rsync -a --chown=root:root "$REPO_DIR/static/" "$APP_DIR/static/"
chmod -R a+rX "$APP_DIR/templates" "$APP_DIR/static"
municipal-manage check --deploy --fail-level WARNING
municipal-manage collectstatic --noinput
restorecon -R /var/www/delegaciones-static
systemctl restart delegaciones
systemctl is-active delegaciones
printf 'Interfaz actualizada. Respaldo: %s\n' "$BACKUP_FILE"

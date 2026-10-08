#!/bin/sh
set -eu
cd /app
python scripts/certificado_local.py
python manage.py migrate --noinput
python scripts/demo.py
python manage.py check --deploy
exec python scripts/serve_https.py

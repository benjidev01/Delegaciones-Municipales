#!/bin/sh
set -eu
cd /app
python manage.py migrate --noinput
if [ "${SEED_DEMO:-false}" = "true" ]; then
  python scripts/demo.py
fi
python manage.py collectstatic --noinput
python manage.py check --deploy --fail-level WARNING
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 \
  --workers 2 --threads 2 --timeout 30 --access-logfile - --error-logfile - \
  --forwarded-allow-ips ''

#!/bin/sh
set -eu
cd /app
python manage.py migrate --noinput
python scripts/demo.py
python manage.py check
exec python manage.py runserver 0.0.0.0:8000 --noreload

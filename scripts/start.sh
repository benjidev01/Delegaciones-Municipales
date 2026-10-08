#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
.venv/bin/python scripts/prepare.py
.venv/bin/python manage.py migrate --noinput
.venv/bin/python scripts/demo.py
exec .venv/bin/python manage.py runserver 127.0.0.1:8000 --noreload

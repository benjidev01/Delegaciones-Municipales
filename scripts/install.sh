#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
export UV_CACHE_DIR="$PWD/.local/uv-cache"
uv venv --allow-existing .venv
uv pip install --python .venv/bin/python --require-hashes -r requirements.lock
.venv/bin/python scripts/prepare.py
.venv/bin/python manage.py migrate --noinput
.venv/bin/python scripts/demo.py
.venv/bin/python manage.py check

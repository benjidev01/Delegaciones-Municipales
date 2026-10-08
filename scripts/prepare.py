"""Prepare only a local development database; never print credentials."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import time

ROOT = Path(__file__).resolve().parent.parent
LOCAL = ROOT / '.local'
LOCAL.mkdir(exist_ok=True, mode=0o700)
path = LOCAL / 'config.json'
if not path.exists():
    values = {'DJANGO_SECRET_KEY': secrets.token_urlsafe(60), 'DJANGO_DEBUG': 'true',
              'POSTGRES_PASSWORD': secrets.token_urlsafe(32), 'POSTGRES_PORT': '55432'}
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(values, stream)
config = json.loads(path.read_text())
name = 'delegaciones-postgres-dev'
exists = subprocess.run(['docker', 'container', 'inspect', name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
if exists:
    subprocess.run(['docker', 'start', name], check=True, stdout=subprocess.DEVNULL)
else:
    docker_env = os.environ.copy()
    docker_env.update(POSTGRES_PASSWORD=config['POSTGRES_PASSWORD'], POSTGRES_USER='delegaciones', POSTGRES_DB='delegaciones')
    subprocess.run(['docker', 'run', '-d', '--name', name, '-p', '127.0.0.1:55432:5432',
                    '-e', 'POSTGRES_PASSWORD', '-e', 'POSTGRES_USER', '-e', 'POSTGRES_DB',
                    '-v', 'delegaciones-pgdata:/var/lib/postgresql/data',
                    'postgres:17@sha256:2d2b8998d31037bf721cfdf764d76ba74171b4fab3431b7f72c27c56ddbdf9e3'],
                   env=docker_env, check=True, stdout=subprocess.DEVNULL)
for attempt in range(30):
    ready = subprocess.run(['docker', 'exec', name, 'pg_isready', '-U', 'delegaciones', '-d', 'delegaciones'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if ready.returncode == 0:
        print('PostgreSQL local disponible. Configuración privada en .local/config.json.')
        break
    time.sleep(1)
else:
    raise SystemExit('PostgreSQL no respondió; revise el contenedor de desarrollo.')

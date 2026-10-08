"""Initialize private development configuration in a persistent Docker volume."""
import json
import os
from pathlib import Path
import secrets

root = Path(__file__).resolve().parent.parent
local = root / '.local'
local.mkdir(exist_ok=True, mode=0o700)
config_file = local / 'config.json'
if not config_file.exists():
    values = {'DJANGO_SECRET_KEY': secrets.token_urlsafe(60), 'DJANGO_DEBUG': 'true',
              'POSTGRES_PASSWORD': secrets.token_urlsafe(32)}
    fd = os.open(config_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(values, stream)
values = json.loads(config_file.read_text())
password_file = local / 'postgres-password.txt'
if not password_file.exists():
    fd = os.open(password_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream:
        stream.write(values['POSTGRES_PASSWORD'])
elif not secrets.compare_digest(password_file.read_text(), values['POSTGRES_PASSWORD']):
    raise SystemExit('La configuración privada no coincide. Revise los volúmenes conservados sin eliminar sus datos.')
print('Configuración privada de desarrollo preparada; no se muestran credenciales.')

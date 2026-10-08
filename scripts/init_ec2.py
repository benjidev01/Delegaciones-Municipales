"""Initialize distinct application and database-admin secrets without displaying them."""
import os
from pathlib import Path
import runpy
import secrets

root = Path(__file__).resolve().parent.parent
runpy.run_path(str(root / 'scripts/init_container.py'))
path = Path('/run/db-admin/password.txt')
if not path.exists():
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'w') as stream:
        stream.write(secrets.token_urlsafe(40))
print('Secretos de EC2 preparados en volúmenes separados; sin mostrar valores.')

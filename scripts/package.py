"""Create a reviewable source bundle without private configuration or databases."""
import hashlib
import os
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / 'dist'
DIST.mkdir(exist_ok=True)
target = DIST / 'Delegaciones-Municipales-demo.zip'
directories = {'apps', 'config', 'deploy', 'docs', 'scripts', 'static', 'templates', 'vendor'}
files = {'.gitignore', '.dockerignore', 'Dockerfile', 'compose.yaml', 'compose.https.yaml', 'manage.py', 'README.md',
         'requirements.txt', 'requirements.lock', 'requirements-dev.txt',
         'Dockerfile.ec2', 'compose.ec2.yaml', 'requirements-prod.txt', 'requirements-prod.lock'}
excluded = {'.git', '.local', '.venv', '__pycache__', 'dist', 'staticfiles'}

with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
    for directory, names, filenames in os.walk(ROOT):
        current = Path(directory)
        names[:] = sorted(name for name in names if name not in excluded and
                          (current != ROOT or name in directories))
        for filename in sorted(filenames):
            path = current / filename
            if current == ROOT and filename not in files:
                continue
            if filename.endswith(('.pyc', '.log')) or filename in {'.env', '.coverage'}:
                continue
            if path.is_symlink():
                raise SystemExit(f'No se incluyen enlaces simbólicos: {path.relative_to(ROOT)}')
            archive.write(path, Path('Delegaciones-Municipales') / path.relative_to(ROOT))

with zipfile.ZipFile(target) as archive:
    if archive.testzip() is not None:
        raise SystemExit('El paquete no superó la comprobación de integridad.')
    names = archive.namelist()
    if any(set(Path(name).parts) & excluded for name in names):
        raise SystemExit('El paquete contiene una ruta privada o generada no permitida.')
    if 'Delegaciones-Municipales/compose.yaml' not in names or not any('/vendor/wheels/' in name for name in names):
        raise SystemExit('Faltan archivos necesarios para ejecutar la demostración.')

digest = hashlib.sha256(target.read_bytes()).hexdigest()
(DIST / (target.name + '.sha256')).write_text(f'{digest}  {target.name}\n')
print(f'Paquete creado: {len(names)} archivos, {target.stat().st_size / 1024 / 1024:.1f} MiB; configuración privada excluida.')

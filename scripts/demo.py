"""Create fictional demonstration data once; preserve existing accounts."""
import json
import os
from pathlib import Path
import secrets
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.db import transaction
from apps.cuentas.models import Usuario
from apps.delegaciones.models import Delegacion
from apps.vecinos.models import Vecino
from apps.solicitudes.services import crear_solicitud

credentials_path = Path(os.environ.get('DJANGO_DEMO_CREDENTIALS_FILE', ROOT / '.local' / 'demo-credentials.json'))
credentials = json.loads(credentials_path.read_text()) if credentials_path.exists() else {}
with transaction.atomic():
    norte, _ = Delegacion.objects.get_or_create(nombre='Delegación Norte (Demo)', defaults={'direccion': 'Avenida Ejemplo 100'})
    sur, _ = Delegacion.objects.get_or_create(nombre='Delegación Sur (Demo)', defaults={'direccion': 'Calle Ficticia 200'})
    for username, role, delegation in [
        ('admin.demo', 'administrador', None), ('delegado.norte', 'delegado', norte),
        ('funcionario.norte', 'funcionario', norte), ('funcionario.sur', 'funcionario', sur),
    ]:
        if not Usuario.objects.filter(username=username).exists():
            password = secrets.token_urlsafe(18)
            user = Usuario(username=username, rol=role, delegacion=delegation,
                           is_staff=role == 'administrador', is_superuser=role == 'administrador')
            user.set_password(password)
            user.full_clean()
            user.save()
            credentials[username] = password
    vecino, _ = Vecino.objects.get_or_create(delegacion=norte, rut='12345678-5', defaults={
        'nombre': 'Vecina de Ejemplo', 'email': 'vecina@example.invalid', 'direccion': 'Pasaje Ficticio 10'})
    if not vecino.solicitud_set.exists():
        crear_solicitud(Usuario.objects.get(username='funcionario.norte'), vecino, 'reclamo',
                       'Ejemplo ficticio: solicitar revisión de luminaria en una plaza.')
fd = os.open(credentials_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(fd, 'w') as stream:
    json.dump(credentials, stream, indent=2)
print('Datos ficticios preparados. Credenciales en el archivo privado configurado; no versionar.')

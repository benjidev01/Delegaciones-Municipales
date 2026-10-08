"""A health check must confirm a functional login form, not only an open port."""
from urllib.request import urlopen
import os
from pathlib import Path
import ssl

tls = os.environ.get('LOCAL_HTTPS') == 'true'
context = ssl.create_default_context(cafile=str(Path(__file__).resolve().parent.parent / '.local/tls/localhost.crt')) if tls else None
scheme = 'https' if tls else 'http'
with urlopen(f'{scheme}://127.0.0.1:8000/acceso/', timeout=3, context=context) as response:
    page = response.read().decode()
    if response.status != 200 or 'Ingresar al sistema' not in page or 'csrfmiddlewaretoken' not in page:
        raise SystemExit('El formulario de acceso aún no está disponible.')

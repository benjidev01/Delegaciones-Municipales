"""Verify private Gunicorn readiness without publishing its port."""
from urllib.request import Request, urlopen

request = Request('http://127.0.0.1:8000/acceso/', headers={'X-Forwarded-Proto': 'https'})
with urlopen(request, timeout=3) as response:
    content = response.read().decode()
    if response.status != 200 or 'Ingresar al sistema' not in content or 'csrfmiddlewaretoken' not in content:
        raise SystemExit('El acceso de la aplicación aún no está disponible.')

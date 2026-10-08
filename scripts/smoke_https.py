"""Exercise local TLS with certificate validation and ephemeral fictional login."""
import http.cookiejar
import os
from pathlib import Path
import re
import secrets
import ssl
import subprocess
import sys
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import build_opener, HTTPCookieProcessor, HTTPSHandler, Request

root = Path(__file__).resolve().parent.parent
base = os.environ.get('SMOKE_BASE_URL', 'https://localhost:8000')
env = os.environ.copy()
env['QA_TLS_USER'] = 'qa.tls.' + secrets.token_hex(6)
env['QA_TLS_PASSWORD'] = secrets.token_urlsafe(24)


def shell(code):
    return subprocess.run(['docker', 'compose', 'exec', '-T', '-e', 'QA_TLS_USER',
        '-e', 'QA_TLS_PASSWORD', 'web', 'python', 'manage.py', 'shell', '--no-imports',
        '-c', code], cwd=root, env=env, check=True, capture_output=True, text=True)


context = ssl.create_default_context(cafile=sys.argv[1])
jar = http.cookiejar.CookieJar()
client = build_opener(HTTPSHandler(context=context), HTTPCookieProcessor(jar))
shell("import os; from apps.cuentas.models import Usuario; from apps.delegaciones.models import Delegacion; "
      "u=Usuario(username=os.environ['QA_TLS_USER'],delegacion=Delegacion.objects.get(nombre='Delegación Norte (Demo)')); "
      "u.set_password(os.environ['QA_TLS_PASSWORD']); u.full_clean(); u.save()")
try:
    with client.open(base + '/acceso/', timeout=5) as response:
        token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', response.read().decode())[1]
    login = Request(base + '/acceso/', data=urlencode({'username': env['QA_TLS_USER'],
        'password': env['QA_TLS_PASSWORD'], 'csrfmiddlewaretoken': token}).encode(),
        headers={'Referer': base + '/acceso/'})
    with client.open(login, timeout=5) as response:
        assert response.url.rstrip('/') == base.rstrip('/')
        assert b'Delegaciones Municipales' in response.read()
        assert response.headers['X-Content-Type-Options'] == 'nosniff'
        assert response.headers['Strict-Transport-Security']
    session = next(cookie for cookie in jar if cookie.name == 'sessionid')
    assert session.secure and session.has_nonstandard_attr('HttpOnly')
    with client.open(base + '/static/app.css', timeout=5) as response:
        assert response.status == 200
    with client.open(base + '/static/sesion.js', timeout=5) as response:
        assert response.status == 200
    try:
        client.open(Request(base + '/sesion/actividad/', data=b'',
                            headers={'Referer': base + '/'}), timeout=5)
        raise AssertionError('CSRF no rechazó una petición sin token')
    except HTTPError as error:
        assert error.code == 403
    token = next(cookie.value for cookie in jar if cookie.name == 'csrftoken')
    with client.open(Request(base + '/sesion/actividad/', data=b'',
            headers={'Referer': base + '/', 'X-CSRFToken': token}), timeout=5) as response:
        assert response.status == 200 and b'"activa": true' in response.read()
    shell("import os; from django.contrib.sessions.models import Session; from apps.cuentas.models import Usuario; from time import time; "
          "uid=str(Usuario.objects.get(username=os.environ['QA_TLS_USER']).pk); "
          "sessions=[s for s in Session.objects.all() if s.get_decoded().get('_auth_user_id')==uid]; "
          "[(setattr(s,'session_data',s.get_session_store_class()().encode(dict(s.get_decoded(),ultima_actividad=time()-1801))),s.save(update_fields=['session_data'])) for s in sessions]")
    with client.open(base + '/vecinos/', timeout=5) as response:
        assert '/acceso/' in response.url
        assert b'id_username' in response.read()
finally:
    shell("import os; from apps.cuentas.models import Usuario; Usuario.objects.filter(username=os.environ['QA_TLS_USER']).update(is_active=False)")
print('HTTPS verificado: certificado confiable, login, cookies seguras, estáticos, CSRF e inactividad. Cuenta QA desactivada.')

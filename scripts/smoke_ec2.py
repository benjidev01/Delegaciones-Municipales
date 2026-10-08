"""Verify the EC2 stack against the operator's endpoint, without AWS API access.

Run explicitly on a prepared stack. Creates synthetic requests and temporary QA
accounts, then disables the QA accounts. Default TLS verification uses public
trust roots; --ca is only for an isolated local rehearsal certificate.
"""
import argparse
import http.cookiejar
import json
import os
from pathlib import Path
import secrets
import ssl
import subprocess
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import build_opener, HTTPCookieProcessor, HTTPSHandler, Request

from ec2_config import ROOT, read_config

parser = argparse.ArgumentParser()
parser.add_argument('--ca')
arguments = parser.parse_args()
public_ip = read_config()['PUBLIC_IP']
base = os.environ.get('SMOKE_BASE_URL', 'https://' + public_ip).rstrip('/')
if not base.startswith('https://'):
    raise SystemExit('La comprobación requiere HTTPS.')
prefix = 'qa.ec2.' + secrets.token_hex(6)
env = os.environ.copy()
env['QA_PREFIX'], env['QA_PASSWORD'] = prefix, secrets.token_urlsafe(24)
context = ssl.create_default_context(cafile=arguments.ca)


def shell(code):
    return subprocess.run(['docker', 'compose', '--env-file', '.local/ec2.env', '-f',
        'compose.ec2.yaml', 'exec', '-T', '-e', 'QA_PREFIX', '-e', 'QA_PASSWORD',
        'web', 'python', 'manage.py', 'shell', '--no-imports', '-c', code],
        cwd=ROOT, env=env, check=True, capture_output=True, text=True)


def client():
    jar = http.cookiejar.CookieJar()
    opener = build_opener(HTTPSHandler(context=context), HTTPCookieProcessor(jar))
    # The local rehearsal connects to localhost while exercising the IP Host.
    opener.addheaders = [('Host', public_ip)]
    return opener, jar


def get(opener, path):
    with opener.open(Request(base + path, headers={'Host': public_ip}), timeout=10) as response:
        return response.url, response.read().decode(), response.headers


def post(opener, jar, path, data, csrf=True):
    headers = {'Referer': 'https://' + public_ip + '/', 'Host': public_ip}
    if csrf:
        headers['X-CSRFToken'] = next(cookie.value for cookie in jar if cookie.name == 'csrftoken')
    with opener.open(Request(base + path, data=urlencode(data).encode(), headers=headers), timeout=10) as response:
        return response.url, response.read().decode(), response.headers


def login(suffix):
    opener, jar = client()
    get(opener, '/acceso/')
    url, _, _ = post(opener, jar, '/acceso/', {'username': prefix + '.' + suffix, 'password': env['QA_PASSWORD']})
    assert url.rstrip('/') == base
    session = next(cookie for cookie in jar if cookie.name == 'sessionid')
    assert session.secure and session.has_nonstandard_attr('HttpOnly')
    return opener, jar


setup = '''
import os, json
from apps.cuentas.models import Usuario
from apps.delegaciones.models import Delegacion
from apps.vecinos.models import Vecino
from django.db import connection
from pathlib import Path
with connection.cursor() as cursor:
    cursor.execute('SELECT rolsuper, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname=current_user')
    assert not any(cursor.fetchone())
assert not Path('/run/db-admin/password.txt').exists()
ids={}
for suffix, role, name in [('func','funcionario','Delegación Norte (Demo)'),
                          ('del','delegado','Delegación Norte (Demo)'),
                          ('sur','funcionario','Delegación Sur (Demo)'),
                          ('admin','administrador',None)]:
    delegation=Delegacion.objects.get(nombre=name) if name else None
    user=Usuario(username=os.environ['QA_PREFIX']+'.'+suffix,rol=role,delegacion=delegation,
                 is_staff=role=='administrador',is_superuser=role=='administrador')
    user.set_password(os.environ['QA_PASSWORD']); user.full_clean(); user.save()
    ids[suffix]=user.pk
ids['vecino']=Vecino.objects.get(rut='12345678-5',delegacion__nombre='Delegación Norte (Demo)').pk
print(json.dumps(ids))
'''
cleanup = '''
import os
from apps.cuentas.models import Usuario
Usuario.objects.filter(username__startswith=os.environ['QA_PREFIX']+'.').update(is_active=False)
'''
ids = json.loads(shell(setup).stdout)
try:
    funcionario, employee_jar = login('func')
    delegado, delegate_jar = login('del')
    _, login_page, headers = get(funcionario, '/')
    assert headers['X-Content-Type-Options'] == 'nosniff'
    assert headers['Strict-Transport-Security']
    assert headers['Cache-Control'].find('no-store') >= 0
    for asset in ('app.css', 'sesion.js'):
        get(funcionario, '/static/' + asset)
    url, page, _ = post(funcionario, employee_jar, '/solicitudes/nueva/', {
        'vecino': ids['vecino'], 'tipo': 'reclamo', 'descripcion': '<script>alert(1)</script>'})
    path = url.removeprefix(base)
    assert path.startswith('/solicitudes/') and '&lt;script&gt;alert(1)&lt;/script&gt;' in page
    for opener, jar, previous, following in [
        (delegado, delegate_jar, 'ingresada', 'asignada'),
        (funcionario, employee_jar, 'asignada', 'atencion'),
        (funcionario, employee_jar, 'atencion', 'resuelta'),
        (delegado, delegate_jar, 'resuelta', 'cerrada')]:
        _, page, _ = post(opener, jar, path + 'estado/', {
            'esperado': previous, 'nuevo': following, 'responsable': ids['func'],
            'motivo': 'Prueba ficticia del despliegue EC2: ' + following})
    assert 'Cerrada' in page
    _, report, _ = get(delegado, '/reportes/?estado=cerrada')
    assert 'report-total' in report
    for opener, forbidden, expected in [(funcionario, '/reportes/', 403),
                                         (funcionario, '/auditoria/', 403),
                                         (login('sur')[0], path, 404)]:
        try:
            get(opener, forbidden)
            raise AssertionError('Acceso no autorizado permitido')
        except HTTPError as error:
            assert error.code == expected
    try:
        post(funcionario, employee_jar, '/sesion/actividad/', {}, csrf=False)
        raise AssertionError('CSRF ausente no fue rechazado')
    except HTTPError as error:
        assert error.code == 403
    admin, _ = login('admin')
    assert 'solicitud.cerrada' in get(admin, '/auditoria/')[1]
finally:
    shell(cleanup)
out = ROOT / '.local/ec2-smoke.json'
out.write_text(json.dumps({'resultado': 'OK', 'verificacion_tls': 'CA local de ensayo' if arguments.ca else 'confianza pública',
    'comprobaciones': ['gunicorn_nginx', 'login_https', 'cookies_seguras', 'csrf', 'xss',
                      'ciclo_solicitud', 'reportes', 'aislamiento', 'auditoria', 'estaticos',
                      'db_sin_superusuario', 'web_sin_secreto_admin'],
    'cuentas_qa': 'desactivadas'}, ensure_ascii=False, indent=2) + '\n')
print('Stack EC2 verificado; TLS validado y cuentas ficticias de prueba desactivadas.')

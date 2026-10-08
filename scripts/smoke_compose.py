"""Verify Docker's real HTTP workflow with temporary fictional accounts.

Requires Docker Compose, Playwright and Chromium on the machine running this
optional verifier. It never reads or prints the demonstration passwords.
"""
from datetime import timedelta
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import uuid

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
BASE = os.environ.get('SMOKE_BASE_URL', 'http://127.0.0.1:8000').rstrip('/')
OUT = ROOT / '.local/browser'
OUT.mkdir(exist_ok=True)
prefix = 'qa.' + uuid.uuid4().hex[:10]
password = secrets.token_urlsafe(24)
process_env = os.environ.copy()
process_env['QA_PREFIX'] = prefix
process_env['QA_PASSWORD'] = password


def shell(code):
    return subprocess.run(['docker', 'compose', 'exec', '-T', '-e', 'QA_PREFIX', '-e', 'QA_PASSWORD',
        'web', 'python', 'manage.py', 'shell', '--no-imports', '-c', code], cwd=ROOT,
        env=process_env, check=True, capture_output=True, text=True)


setup = '''
import os
from apps.cuentas.models import Usuario
from apps.delegaciones.models import Delegacion
for suffix, role, name in [('func','funcionario','Delegación Norte (Demo)'),
                            ('del','delegado','Delegación Norte (Demo)'),
                            ('sur','funcionario','Delegación Sur (Demo)'),
                            ('admin','administrador',None)]:
    delegation = Delegacion.objects.get(nombre=name) if name else None
    user = Usuario(username=os.environ['QA_PREFIX']+'.'+suffix, rol=role, delegacion=delegation,
                   is_staff=role=='administrador', is_superuser=role=='administrador')
    user.set_password(os.environ['QA_PASSWORD'])
    user.full_clean()
    user.save()
'''
cleanup = '''
import os
from apps.cuentas.models import Usuario
from apps.agenda.models import Cita
from apps.agenda.services import cambiar_estado
prefix = os.environ['QA_PREFIX']+'.'
actor = Usuario.objects.filter(username=prefix+'admin').first()
if actor:
    for cita in Cita.objects.filter(funcionario__username__startswith=prefix, estado='programada'):
        cambiar_estado(actor, cita.pk, 'programada', 'cancelada', 'Fin de la comprobación Docker con datos ficticios')
Usuario.objects.filter(username__startswith=prefix).update(is_active=False)
'''


def login(browser, suffix):
    context = browser.new_context(viewport={'width': 1280, 'height': 900}, locale='es-CL')
    page = context.new_page()
    response = page.goto(BASE + '/acceso/')
    assert response.status == 200
    page.locator('#id_username').fill(prefix + '.' + suffix)
    page.locator('#id_password').fill(password)
    page.get_by_role('button', name='Ingresar al sistema').click()
    page.wait_for_url(BASE + '/')
    return context, page


shell(setup)
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox'])
        contexts = []
        context, page = login(browser, 'func')
        contexts.append(context)
        page.goto(BASE + '/solicitudes/nueva/')
        page.locator('#id_vecino').select_option(label='Vecina de Ejemplo · 12345678-5')
        page.locator('#id_tipo').select_option('reclamo')
        page.locator('#id_descripcion').fill('Verificación funcional de la distribución Docker con datos ficticios.')
        page.get_by_role('button', name='Guardar', exact=True).click()
        page.wait_for_url(re.compile(r'/solicitudes/\d+/$'))
        url = page.url

        context, delegate = login(browser, 'del')
        contexts.append(context)
        delegate.goto(url)
        delegate.locator('#id_responsable').select_option(label=prefix + '.func')
        delegate.locator('#id_motivo').fill('Asignación de prueba Docker')
        delegate.get_by_role('button', name='Confirmar cambio de estado').click()
        page.reload()
        for text, expected in [('Inicio de atención Docker', 'En atención'), ('Solución ficticia verificada', 'Resuelta')]:
            page.locator('#id_motivo').fill(text)
            page.get_by_role('button', name='Confirmar cambio de estado').click()
            assert page.locator('.badge').inner_text() == expected
        delegate.reload()
        delegate.locator('#id_motivo').fill('Cierre de prueba Docker')
        delegate.get_by_role('button', name='Confirmar cambio de estado').click()
        assert delegate.locator('.badge').inner_text() == 'Cerrada'
        assert delegate.locator('.timeline li').count() == 4

        page.goto(BASE + '/agenda/nueva/')
        page.locator('#id_vecino').select_option(label='Vecina de Ejemplo · 12345678-5')
        page.locator('#id_funcionario').select_option(label=prefix + '.func')
        # The browser verifier runs on the same cloud machine. Choose a date
        # from the Django application's clock without touching credentials.
        result = shell("from django.utils import timezone; from datetime import timedelta; print(timezone.localtime(timezone.now()+timedelta(days=2)).replace(hour=10, minute=0, second=0, microsecond=0).strftime('%Y-%m-%dT%H:%M'))")
        page.locator('#id_inicio').fill(result.stdout.strip())
        page.locator('#id_duracion').select_option('30')
        page.locator('#id_motivo').fill('Reserva ficticia para prueba Docker')
        page.get_by_role('button', name='Guardar', exact=True).click()
        page.wait_for_url(re.compile(r'/agenda/\d+/$'))
        cita_url = page.url
        assert page.locator('.badge').inner_text() == 'Programada'
        page.locator('#id_nuevo').select_option('cancelada')
        page.locator('#id_motivo').fill('Cancelación de prueba Docker')
        page.get_by_role('button', name='Confirmar acción').click()
        assert page.locator('.badge').inner_text() == 'Cancelada'

        delegate.goto(BASE + '/reportes/?estado=cerrada')
        assert int(delegate.locator('.report-total strong').inner_text()) >= 1
        assert page.goto(BASE + '/reportes/').status == 403
        page.goto(BASE + '/vecinos/')
        page.clock.install()
        # Force only this QA account's last-activity time into the past. The
        # private page must reject its still-existing session immediately.
        shell("from django.contrib.sessions.models import Session; from time import time; from apps.cuentas.models import Usuario; uid=str(Usuario.objects.get(username=os.environ['QA_PREFIX']+'.func').pk); "
              "sessions=[s for s in Session.objects.all() if s.get_decoded().get('_auth_user_id')==uid]; "
              "[(setattr(s, 'session_data', s.get_session_store_class()().encode(dict(s.get_decoded(), ultima_actividad=time()-1801))), s.save(update_fields=['session_data'])) for s in sessions]")
        page.clock.fast_forward(1801000)
        page.wait_for_url('**/acceso/')
        assert '/acceso/' in page.url
        assert page.locator('#id_username').count() == 1
        context, other = login(browser, 'sur')
        contexts.append(context)
        assert other.goto(url).status == 404
        assert other.goto(cita_url).status == 404
        context, admin = login(browser, 'admin')
        contexts.append(context)
        admin.goto(BASE + '/auditoria/')
        assert admin.get_by_text('cita.cancelada', exact=True).count() > 0
        for context in contexts:
            context.close()
        browser.close()
finally:
    shell(cleanup)

(OUT / 'docker.json').write_text(json.dumps({'result': 'passed', 'checks': [
    'login', 'ciclo_solicitud', 'agenda', 'cancelacion', 'reportes', 'aislamiento', 'auditoria', 'inactividad_servidor_y_navegador'],
    'test_accounts': 'disabled_after_execution'}, indent=2))
print('Distribución Docker verificada en navegador; cuentas ficticias de prueba desactivadas.')

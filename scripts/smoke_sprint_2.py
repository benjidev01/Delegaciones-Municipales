"""Functional browser check for appointments and reports using fictional data."""
import json
import os
from pathlib import Path
import re
import sys
from datetime import timedelta

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.utils import timezone
from apps.agenda.models import Cita
from apps.cuentas.models import Usuario
from apps.solicitudes.models import Solicitud

credentials = json.loads((ROOT / '.local/demo-credentials.json').read_text())
OUT = ROOT / '.local/browser'
OUT.mkdir(exist_ok=True)
BASE = 'http://127.0.0.1:8000'
employee = Usuario.objects.get(username='funcionario.norte')
start = timezone.localtime(timezone.now() + timedelta(days=3)).replace(hour=10, minute=0, second=0, microsecond=0)
while Cita.objects.filter(funcionario=employee, estado='programada', inicio__lt=start + timedelta(minutes=30), fin__gt=start).exists():
    start += timedelta(minutes=30)
expected = employee.scope(Solicitud.objects.all()).count()
expected_closed = employee.scope(Solicitud.objects.filter(estado='cerrada')).count()


def login(browser, username, width=1440):
    context = browser.new_context(viewport={'width': width, 'height': 1024})
    page = context.new_page()
    page.goto(BASE + '/acceso/')
    page.locator('#id_username').fill(username)
    page.locator('#id_password').fill(credentials[username])
    page.get_by_role('button', name='Ingresar al sistema').click()
    page.wait_for_url(BASE + '/')
    return context, page


def fill_reserva(page):
    page.goto(BASE + '/agenda/nueva/')
    page.locator('#id_vecino').select_option(label='Vecina de Ejemplo · 12345678-5')
    page.locator('#id_funcionario').select_option(label='funcionario.norte')
    page.locator('#id_inicio').fill(start.strftime('%Y-%m-%dT%H:%M'))
    page.locator('#id_duracion').select_option('30')
    page.locator('#id_motivo').fill('Atención ficticia: orientación sobre solicitud municipal.')


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
    context, page = login(browser, 'funcionario.norte')
    fill_reserva(page)
    page.get_by_role('button', name='Guardar', exact=True).click()
    page.wait_for_url(re.compile(r'/agenda/\d+/$'))
    url = page.url
    assert page.locator('.badge').inner_text() == 'Programada'
    fill_reserva(page)
    page.get_by_role('button', name='Guardar', exact=True).click()
    assert page.locator('.errorlist').inner_text().find('ya tiene una atención') >= 0
    assert page.locator('#id_motivo').input_value().startswith('Atención ficticia')
    page.goto(BASE + '/agenda/')
    page.locator('#id_fecha').fill(start.date().isoformat())
    page.get_by_role('button', name='Filtrar agenda').click()
    assert page.get_by_role('link', name=re.compile('Ver atención')).count() > 0
    page.screenshot(path=str(OUT / 'agenda-pc.png'), full_page=True)
    page.goto(url)
    page.locator('#id_nuevo').select_option('cancelada')
    page.locator('#id_motivo').fill('Cancelación ficticia para verificar liberación del horario.')
    page.get_by_role('button', name='Confirmar acción').click()
    assert page.locator('.badge').inner_text() == 'Cancelada'
    assert page.locator('.timeline li').count() == 1
    fill_reserva(page)
    page.get_by_role('button', name='Guardar', exact=True).click()
    page.wait_for_url(re.compile(r'/agenda/\d+/$'))
    new_url = page.url
    assert new_url != url
    assert page.locator('.badge').inner_text() == 'Programada'
    response = page.goto(BASE + '/reportes/')
    assert response.status == 403

    other_context, other = login(browser, 'funcionario.sur')
    response = other.goto(new_url)
    assert response.status == 404

    delegate_context, delegate = login(browser, 'delegado.norte', width=768)
    delegate.goto(new_url)
    assert delegate.locator('.badge').inner_text() == 'Programada'
    assert delegate.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    delegate.screenshot(path=str(OUT / 'atencion-tablet.png'), full_page=True)
    delegate.goto(BASE + '/reportes/')
    assert int(delegate.locator('.report-total strong').inner_text()) == expected
    delegate.locator('#id_estado').select_option('cerrada')
    delegate.get_by_role('button', name='Consultar reporte').click()
    assert int(delegate.locator('.report-total strong').inner_text()) == expected_closed
    assert delegate.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    delegate.screenshot(path=str(OUT / 'reportes-tablet.png'), full_page=True)
    delegate.locator('#id_desde').fill('2026-10-10')
    delegate.locator('#id_hasta').fill('2026-10-01')
    delegate.get_by_role('button', name='Consultar reporte').click()
    assert delegate.locator('.errorlist').count() > 0
    assert int(delegate.locator('.report-total strong').inner_text()) == 0

    admin_context, admin = login(browser, 'admin.demo')
    admin.goto(BASE + '/reportes/')
    assert admin.locator('#id_delegacion option').count() >= 3
    admin.screenshot(path=str(OUT / 'reportes-pc.png'), full_page=True)
    admin.goto(BASE + '/auditoria/')
    assert admin.get_by_text('cita.reservada', exact=True).count() > 0
    assert admin.get_by_text('cita.cancelada', exact=True).count() > 0

    (OUT / 'sprint-2.json').write_text(json.dumps({'result': 'passed', 'cita_programada': int(new_url.rstrip('/').split('/')[-1]),
        'checks': ['reserva', 'conflicto', 'cancelacion', 'liberacion_horario', 'permisos', 'reportes', 'auditoria', 'pc_tablet']}, indent=2))
    for c in (context, other_context, delegate_context, admin_context):
        c.close()
    browser.close()
print('Navegador aprobado: agenda, rechazo de superposición, cancelación, aislamiento, reportes, auditoría y PC/tablet.')

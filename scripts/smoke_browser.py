"""Exercise the first sprint against a running local server using fictional data."""
import json
from pathlib import Path
import re
import uuid
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
credentials = json.loads((ROOT / '.local/demo-credentials.json').read_text())
BASE = 'http://127.0.0.1:8000'
OUT = ROOT / '.local/browser'
OUT.mkdir(exist_ok=True)

def login(browser, username, viewport):
    context = browser.new_context(viewport=viewport)
    page = context.new_page()
    page.goto(BASE + '/acceso/')
    page.locator('#id_username').fill(username)
    page.locator('#id_password').fill(credentials[username])
    page.get_by_role('button', name='Ingresar al sistema').click()
    page.wait_for_url(BASE + '/')
    return context, page

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
    context, page = login(browser, 'funcionario.norte', {'width': 1440, 'height': 1000})
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.screenshot(path=str(OUT / 'panel-pc.png'), full_page=True)
    page.get_by_role('link', name='Registrar vecino').click()
    page.locator('#id_rut').fill('11111111-1')
    page.locator('#id_nombre').fill('Vecino de Prueba Navegador')
    page.locator('#id_email').fill('prueba@example.invalid')
    page.locator('#id_direccion').fill('Dirección ficticia para pruebas')
    page.get_by_role('button', name='Guardar', exact=True).click()
    # Repeated runs may find the same fictional RUT already registered.
    if page.url.endswith('/vecinos/nuevo/'):
        assert page.locator('.errorlist').count() > 0
    page.goto(BASE + '/solicitudes/nueva/')
    page.locator('#id_vecino').select_option(label='Vecino de Prueba Navegador · 11111111-1')
    page.locator('#id_tipo').select_option('reclamo')
    description = 'Prueba navegador ' + uuid.uuid4().hex[:8] + ': luminaria ficticia.'
    page.locator('#id_descripcion').fill(description)
    page.get_by_role('button', name='Guardar', exact=True).click()
    page.wait_for_url(re.compile(r'/solicitudes/\d+/$'))
    url = page.url
    assert page.get_by_text(description, exact=True).is_visible()
    assert not page.get_by_role('button', name='Confirmar cambio de estado').count()

    delegate_context, delegate = login(browser, 'delegado.norte', {'width': 768, 'height': 1024})
    delegate.goto(url)
    delegate.locator('#id_responsable').select_option(label='funcionario.norte')
    delegate.locator('#id_motivo').fill('Asignación autorizada de prueba.')
    delegate.get_by_role('button', name='Confirmar cambio de estado').click()
    assert delegate.locator('.badge').inner_text() == 'Asignada'
    page.reload()
    page.locator('#id_motivo').fill('Inicio de atención de prueba.')
    page.get_by_role('button', name='Confirmar cambio de estado').click()
    assert page.locator('.badge').inner_text() == 'En atención'
    page.locator('#id_motivo').fill('Solución ficticia documentada.')
    page.get_by_role('button', name='Confirmar cambio de estado').click()
    assert page.locator('.badge').inner_text() == 'Resuelta'
    delegate.reload()
    delegate.locator('#id_motivo').fill('Verificación y cierre de prueba.')
    delegate.get_by_role('button', name='Confirmar cambio de estado').click()
    assert delegate.locator('.badge').inner_text() == 'Cerrada'
    assert delegate.locator('.timeline li').count() == 4
    assert delegate.locator('.note').count() == 4
    assert delegate.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    delegate.screenshot(path=str(OUT / 'solicitud-tablet.png'), full_page=True)

    other_context, other = login(browser, 'funcionario.sur', {'width': 1280, 'height': 900})
    response = other.goto(url)
    assert response.status == 404

    admin_context, admin = login(browser, 'admin.demo', {'width': 1440, 'height': 1000})
    admin.goto(BASE + '/auditoria/')
    assert admin.get_by_role('heading', name='Auditoría').is_visible()
    assert admin.get_by_text('solicitud.cerrada', exact=True).count() > 0
    admin.goto(BASE + '/admin/')
    assert admin.get_by_text('Administración municipal', exact=True).is_visible()

    page.get_by_role('button', name='Salir', exact=True).click()
    page.wait_for_url(BASE + '/acceso/')
    # Django focuses the username automatically on login. Shift+Tab reaches
    # the preceding skip link without relying on browser history focus.
    page.locator('#id_username').focus()
    page.keyboard.press('Shift+Tab')
    assert page.evaluate('document.activeElement.textContent') == 'Saltar al contenido'
    page.keyboard.press('Enter')
    assert page.locator('#contenido').evaluate('(node) => node === document.activeElement')
    assert not errors, errors
    for c in (context, delegate_context, other_context, admin_context):
        c.close()
    browser.close()
print('Prueba de navegador aprobada: registro, ciclo completo, aislamiento, auditoría, PC/tablet y salto por teclado.')

"""Run local axe-core checks; pass its verified local JS path as argument."""
import json
from pathlib import Path
import sys
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
credentials = json.loads((ROOT / '.local/demo-credentials.json').read_text())
axe = Path(sys.argv[1]).resolve()
results = []
routes = ['/acceso/', '/', '/vecinos/', '/vecinos/nuevo/', '/solicitudes/', '/solicitudes/nueva/', '/solicitudes/1/',
          '/agenda/', '/agenda/nueva/', '/reportes/']
result_file = ROOT / '.local/browser/sprint-2.json'
if result_file.exists():
    result = json.loads(result_file.read_text())
    routes.append(f"/agenda/{result['cita_programada']}/")
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
    for width in [1440, 768]:
        context = browser.new_context(viewport={'width': width, 'height': 1024})
        page = context.new_page()
        for route in routes:
            page.goto('http://127.0.0.1:8000' + route)
            if route == '/':
                page.locator('#id_username').fill('delegado.norte')
                page.locator('#id_password').fill(credentials['delegado.norte'])
                page.get_by_role('button', name='Ingresar al sistema').click()
                page.wait_for_url('http://127.0.0.1:8000/')
            page.add_script_tag(path=str(axe))
            audit = page.evaluate("async () => await axe.run(document, {runOnly: {type: 'tag', values: ['wcag2a','wcag2aa','wcag21aa']}})")
            overflow = page.evaluate('document.documentElement.scrollWidth > window.innerWidth')
            results.append({'width': width, 'route': route, 'horizontal_overflow': overflow,
                            'violations': [{'id': v['id'], 'impact': v['impact'],
                                            'targets': [node['target'] for node in v['nodes']]} for v in audit['violations']],
                            'manual_checks_required': [v['id'] for v in audit['incomplete']]})
        context.close()
    browser.close()
output = ROOT / '.local/browser/accessibility.json'
output.parent.mkdir(exist_ok=True)
output.write_text(json.dumps(results, indent=2))
for result in results:
    print(f"{result['width']} {result['route']}: {len(result['violations'])} infracciones, desborde={result['horizontal_overflow']}")
if any(result['violations'] or result['horizontal_overflow'] for result in results):
    raise SystemExit(1)
print('Sin infracciones automáticas en las vistas verificadas; la revisión humana sigue pendiente.')

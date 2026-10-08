"""Create a PDF containing the real screenshots of the second increment."""
import base64
import html
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'docs/evidencias'
OUT.mkdir(exist_ok=True)
screens = [('agenda-pc.png', 'Agenda de atenciones · PC'),
           ('atencion-tablet.png', 'Detalle de atención · Tablet'),
           ('reportes-pc.png', 'Reportes de solicitudes · PC'),
           ('reportes-tablet.png', 'Reportes de solicitudes · Tablet')]
sections = []
for filename, title in screens:
    data = (ROOT / '.local/browser' / filename).read_bytes()
    (OUT / filename).write_bytes(data)
    image = base64.b64encode(data).decode('ascii')
    sections.append(f'<section><h1>{html.escape(title)}</h1><p>Prototipo académico · Datos ficticios</p>'
                    f'<img alt="{html.escape(title)}" src="data:image/png;base64,{image}"></section>')
document = '''<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Agenda y reportes municipales</title>
<style>@page{size:A4 landscape;margin:8mm}body{margin:0;font-family:Arial,sans-serif;color:#163044}section{break-after:page}section:last-child{break-after:auto}h1{font-size:16px;margin:0 0 4px}p{font-size:11px;margin:0 0 6px}img{display:block;max-width:100%;max-height:175mm;margin:auto;object-fit:contain}</style></head><body>'''
document += ''.join(sections) + '</body></html>'
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox'])
    page = browser.new_page()
    page.set_content(document)
    page.locator('img').evaluate_all('(images) => Promise.all(images.map(image => image.decode()))')
    page.pdf(path=str(OUT / 'agenda-y-reportes.pdf'), print_background=True, prefer_css_page_size=True)
    browser.close()
print('Creado docs/evidencias/agenda-y-reportes.pdf con capturas reales del incremento.')

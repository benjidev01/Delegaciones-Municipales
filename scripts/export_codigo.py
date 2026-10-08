"""Export all project-owned source files as a readable HTML review, without secrets."""
from html import escape
from pathlib import Path

root = Path(__file__).resolve().parent.parent
directories = ['apps', 'config', 'deploy', 'scripts', 'static', 'templates']
names = ['manage.py', 'Dockerfile', 'compose.yaml', 'compose.https.yaml',
         '.dockerignore', '.gitignore', 'requirements.txt', 'requirements.lock',
         'requirements-dev.txt', 'Dockerfile.ec2', 'compose.ec2.yaml',
         'requirements-prod.txt', 'requirements-prod.lock']
paths = [root / name for name in names]
for name in directories:
    paths.extend(p for p in (root / name).rglob('*')
                 if p.is_file() and '__pycache__' not in p.parts
                 and p.suffix in {'.py', '.sh', '.html', '.css', '.js', '.template', '.service', '.timer'})
paths = sorted(set(paths))
body = ['<!doctype html><html lang="es"><meta charset="utf-8">',
        '<title>Revisión del código completo</title>',
        '<style>body{font:16px sans-serif;max-width:1200px;margin:auto;padding:24px}'
        'pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f5f6;padding:16px}'
        'a{line-height:1.8}</style><h1>Código completo para revisión</h1>',
        '<p>Incluye código propio, pruebas, migraciones y configuración pública. '
        'Excluye credenciales, datos privados y binarios de dependencias de terceros.</p><ol>']
for index, path in enumerate(paths):
    body.append(f'<li><a href="#f{index}">{escape(str(path.relative_to(root)))}</a></li>')
body.append('</ol>')
for index, path in enumerate(paths):
    if path.is_symlink():
        raise SystemExit('No se exportan enlaces simbólicos.')
    body.append(f'<h2 id="f{index}">{escape(str(path.relative_to(root)))}</h2>'
                f'<pre><code>{escape(path.read_text())}</code></pre>')
body.append('</html>')
target = root / 'docs/codigo-completo.html'
target.write_text('\n'.join(body))
markdown = ['# Código completo para revisión\n',
            'Código propio completo, pruebas, migraciones y configuración pública. '
            'Sin credenciales ni binarios de terceros.\n']
for path in paths:
    markdown.append(f'\n## {path.relative_to(root)}\n\n````\n{path.read_text()}\n````\n')
(root / 'docs/codigo-completo.md').write_text('\n'.join(markdown))
print(f'Código exportado: {len(paths)} archivos completos; sin configuración privada.')

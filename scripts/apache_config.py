"""Generate native private settings and Apache virtual hosts."""
import argparse
import ipaddress
import json
import re
import secrets
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('ip')
parser.add_argument('email')
parser.add_argument('--https', action='store_true')
parser.add_argument('--output', type=Path, default=Path('/etc/httpd/conf.d/delegaciones.conf'))
parser.add_argument('--directory', type=Path, default=Path('/etc/delegaciones'))
args = parser.parse_args()
ip = ipaddress.ip_address(args.ip)
if ip.version != 4 or not ip.is_global or ip.is_multicast:
    parser.error('Use una IPv4 pública válida.')
if not re.fullmatch(r'[A-Za-z0-9._+%-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', args.email):
    parser.error('Correo no válido.')
args.directory.mkdir(parents=True, exist_ok=True)
private = args.directory / 'config.json'
if not private.exists():
    private.write_text(json.dumps({
        'DJANGO_SECRET_KEY': secrets.token_urlsafe(64), 'DJANGO_DEBUG': 'false',
        'DJANGO_ALLOWED_HOSTS': str(ip), 'DJANGO_TRUST_PROXY': 'true',
        'DJANGO_STATIC_ROOT': '/var/www/delegaciones-static',
        'POSTGRES_DB': 'delegaciones', 'POSTGRES_USER': 'delegaciones',
        'POSTGRES_PASSWORD': secrets.token_urlsafe(48),
        'POSTGRES_HOST': '127.0.0.1', 'POSTGRES_PORT': '5432',
    }, indent=2))
    private.chmod(0o600)
else:
    stored = json.loads(private.read_text())
    if stored['DJANGO_ALLOWED_HOSTS'] != str(ip):
        raise SystemExit('La IP cambió: revisar configuración y certificado.')
(args.directory / 'public.json').write_text(json.dumps({'ip': str(ip), 'email': args.email}))
marker = '# Administrado por Delegaciones Municipales\n'
if args.output.exists() and not args.output.read_text().startswith(marker):
    raise SystemExit('No se sobrescribe configuración Apache ajena.')
challenge = '''Alias /.well-known/acme-challenge/ /var/www/delegaciones-acme/.well-known/acme-challenge/
<Directory /var/www/delegaciones-acme>
Options None
AllowOverride None
Require all granted
</Directory>
'''
text = marker + '''ServerTokens Prod
ServerSignature Off
<VirtualHost *:80>
ServerName no-autorizado.invalid
<Location />
Require all denied
</Location>
</VirtualHost>
''' + f'<VirtualHost *:80>\nServerName {ip}\n' + challenge + 'RewriteEngine On\nRewriteCond %{REQUEST_URI} !^/\\.well-known/acme-challenge/\n'
text += (f'RewriteRule ^ https://{ip}%{{REQUEST_URI}} [R=301,L,NE]\n' if args.https else 'RewriteRule ^ - [R=503,L]\n')
text += '</VirtualHost>\n'
if args.https:
    text += f'''Listen 443 https
<VirtualHost *:443>
ServerName {ip}
<Location />
Require expr "%{{HTTP_HOST}} == '{ip}' || %{{HTTP_HOST}} == '{ip}:443'"
</Location>
SSLEngine on
SSLProtocol -all +TLSv1.2 +TLSv1.3
SSLCertificateFile /etc/letsencrypt/live/municipal-ip/fullchain.pem
SSLCertificateKeyFile /etc/letsencrypt/live/municipal-ip/privkey.pem
ProxyRequests Off
ProxyPreserveHost On
ProxyAddHeaders Off
RequestHeader set X-Forwarded-Proto "https"
RequestHeader set X-Real-IP "expr=%{{REMOTE_ADDR}}"
RequestHeader set X-Forwarded-For "expr=%{{REMOTE_ADDR}}"
ProxyPass /static/ !
Alias /static/ /var/www/delegaciones-static/
<Directory /var/www/delegaciones-static>
Options None
AllowOverride None
Require all granted
</Directory>
ProxyPass / "unix:/run/delegaciones/gunicorn.sock|http://localhost/"
ProxyPassReverse / http://localhost/
</VirtualHost>
'''
args.output.write_text(text)
print('Configuración preparada; comprobar httpd -t antes de recargar.')

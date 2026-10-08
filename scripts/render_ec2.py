"""Render public Nginx configuration using a validated IPv4 address."""
import sys
from ec2_config import ROOT, read_config

mode = sys.argv[1]
if mode not in ('http', 'https'):
    raise SystemExit('Modo permitido: http o https.')
values = read_config()
template = (ROOT / f'deploy/ec2/nginx-{mode}.conf.template').read_text()
target = ROOT / '.local/ec2/nginx/default.conf'
target.write_text(template.replace('__PUBLIC_IP__', values['PUBLIC_IP']))
print('Configuración de Nginx preparada. El servidor requiere comprobación y recarga.')

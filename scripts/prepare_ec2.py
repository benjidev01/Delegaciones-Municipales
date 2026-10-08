"""Prepare public metadata and bootstrap configuration without contacting AWS or ACME."""
import argparse
from ipaddress import IPv4Address
import os
from pathlib import Path
import re
from ec2_config import ROOT, CONFIG, read_config

parser = argparse.ArgumentParser()
parser.add_argument('--ip', required=True)
parser.add_argument('--email', required=True)
parser.add_argument('--bind-address', choices=['0.0.0.0', '127.0.0.1'], default='0.0.0.0')
parser.add_argument('--http-port', type=int, default=80)
parser.add_argument('--https-port', type=int, default=443)
arguments = parser.parse_args()
address = IPv4Address(arguments.ip)
if not address.is_global or address.is_multicast:
    parser.error('La dirección debe ser una IPv4 pública estable.')
if not re.fullmatch(r'[A-Za-z0-9._+%-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', arguments.email):
    parser.error('El correo no es válido.')
if not all(1 <= value <= 65535 for value in (arguments.http_port, arguments.https_port)):
    parser.error('Los puertos deben estar entre 1 y 65535.')
if arguments.http_port == arguments.https_port:
    parser.error('Los puertos HTTP y HTTPS deben ser distintos.')
(ROOT / '.local').mkdir(mode=0o700, exist_ok=True)
values = {'PUBLIC_IP': arguments.ip, 'ACME_EMAIL': arguments.email,
          'BIND_ADDRESS': arguments.bind_address, 'HTTP_PORT': str(arguments.http_port),
          'HTTPS_PORT': str(arguments.https_port)}
if CONFIG.exists():
    if read_config() != values:
        raise SystemExit('Ya existe otra configuración. Revise .local/ec2.env; no se sobrescribió.')
else:
    descriptor = os.open(CONFIG, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'w') as stream:
        stream.write(''.join(f'{key}={value}\n' for key, value in values.items()))
directory = ROOT / '.local/ec2/nginx'
directory.mkdir(parents=True, exist_ok=True)
target = directory / 'default.conf'
if not target.exists():
    template = (ROOT / 'deploy/ec2/nginx-http.conf.template').read_text()
    target.write_text(template.replace('__PUBLIC_IP__', arguments.ip))
print('Configuración EC2 preparada localmente; no se inició ningún servicio ni se emitió un certificado.')

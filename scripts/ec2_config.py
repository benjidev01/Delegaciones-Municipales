"""Validate public deployment metadata; never read or emit application secrets."""
from ipaddress import IPv4Address
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / '.local/ec2.env'


def read_config():
    values = dict(line.split('=', 1) for line in CONFIG.read_text().splitlines()
                  if line and not line.startswith('#'))
    address = IPv4Address(values['PUBLIC_IP'])
    if not address.is_global or address.is_multicast:
        raise ValueError('Se necesita una IPv4 pública; no usar direcciones privadas o de documentación.')
    email = values['ACME_EMAIL']
    if not re.fullmatch(r'[A-Za-z0-9._+%-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', email):
        raise ValueError('Indique un correo válido para ACME.')
    if values['BIND_ADDRESS'] not in ('0.0.0.0', '127.0.0.1'):
        raise ValueError('Dirección de escucha no permitida.')
    for key in ('HTTP_PORT', 'HTTPS_PORT'):
        if not 1 <= int(values[key]) <= 65535:
            raise ValueError('Puerto fuera de rango.')
    return values


if __name__ == '__main__':
    key = {'ip': 'PUBLIC_IP', 'email': 'ACME_EMAIL'}[sys.argv[1]]
    print(read_config()[key])

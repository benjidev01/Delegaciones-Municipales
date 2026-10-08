"""Generate a private, self-signed localhost certificate for academic TLS tests."""
import os
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parent.parent / '.local' / 'tls'
root.mkdir(mode=0o700, exist_ok=True)
key, cert = root / 'localhost.key', root / 'localhost.crt'
if key.exists() != cert.exists():
    raise SystemExit('Certificado local incompleto. Revise .local/tls sin eliminar otros datos.')
if not cert.exists():
    previous = os.umask(0o077)
    try:
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:3072', '-sha256',
            '-nodes', '-days', '365', '-subj', '/CN=localhost',
            '-addext', 'subjectAltName=DNS:localhost,IP:127.0.0.1',
            '-addext', 'basicConstraints=critical,CA:TRUE',
            '-keyout', str(key), '-out', str(cert)], check=True, capture_output=True)
    finally:
        os.umask(previous)
    cert.chmod(0o644)
print('Certificado público local disponible; clave privada conservada en el volumen.')

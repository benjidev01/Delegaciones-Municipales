"""Local threaded TLS server for the evaluation, never a production server."""
import os
from pathlib import Path
import ssl
import sys
from socketserver import ThreadingMixIn
from wsgiref.simple_server import WSGIServer, WSGIRequestHandler, make_server

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
from django.core.wsgi import get_wsgi_application
from django.contrib.staticfiles.handlers import StaticFilesHandler


class LocalTLSServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


class TLSRequestHandler(WSGIRequestHandler):
    def get_environ(self):
        environ = super().get_environ()
        environ['HTTPS'] = 'on'
        return environ


application = StaticFilesHandler(get_wsgi_application())
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.minimum_version = ssl.TLSVersion.TLSv1_2
context.load_cert_chain(ROOT / '.local/tls/localhost.crt', ROOT / '.local/tls/localhost.key')
with make_server('0.0.0.0', 8000, application, server_class=LocalTLSServer,
                 handler_class=TLSRequestHandler) as server:
    server.socket = context.wrap_socket(server.socket, server_side=True)
    print('Demostración HTTPS local iniciada; no apta para publicación en Internet.', flush=True)
    server.serve_forever()

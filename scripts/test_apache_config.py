"""Validate configuration rendering without touching system files."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).with_name('apache_config.py')

class ApacheConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output = self.root / 'site.conf'

    def render(self, ip='8.8.8.8', email='test@example.com', https=False):
        return subprocess.run([sys.executable, str(SCRIPT), ip, email,
            '--directory', str(self.root / 'private'), '--output', str(self.output)]
            + (['--https'] if https else []), capture_output=True, text=True)

    def test_bootstrap_does_not_publish_application(self):
        self.assertEqual(self.render().returncode, 0)
        text = self.output.read_text()
        self.assertIn('[R=503,L]', text)
        self.assertNotIn('ProxyPass / ', text)
        self.assertIn('/.well-known/acme-challenge/', text)
        self.assertEqual((self.root / 'private/config.json').stat().st_mode & 0o777, 0o600)

    def test_https_overwrites_headers_and_uses_private_socket(self):
        self.assertEqual(self.render(https=True).returncode, 0)
        text = self.output.read_text()
        self.assertIn('RequestHeader set X-Real-IP "expr=%{REMOTE_ADDR}"', text)
        self.assertIn('RequestHeader set X-Forwarded-Proto "https"', text)
        self.assertIn('unix:/run/delegaciones/gunicorn.sock', text)
        self.assertIn('ProxyPass /static/ !', text)

    def test_repetition_preserves_private_configuration(self):
        self.assertEqual(self.render().returncode, 0)
        path = self.root / 'private/config.json'
        before = path.read_bytes()
        self.assertEqual(self.render(https=True).returncode, 0)
        self.assertEqual(before, path.read_bytes())
        self.assertNotEqual(self.render(ip='1.1.1.1').returncode, 0)
        self.assertEqual(before, path.read_bytes())

    def test_rejects_private_ip_and_configuration_injection(self):
        self.assertNotEqual(self.render(ip='127.0.0.1').returncode, 0)
        self.assertNotEqual(self.render(email='a@example.com\nListen 9000').returncode, 0)
        self.assertFalse(self.output.exists())

    def test_preserves_unmanaged_apache_file(self):
        self.output.write_text('A user-owned virtual host\n')
        self.assertNotEqual(self.render().returncode, 0)
        self.assertEqual(self.output.read_text(), 'A user-owned virtual host\n')

if __name__ == '__main__':
    unittest.main()

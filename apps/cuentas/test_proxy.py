from django.test import RequestFactory, SimpleTestCase, override_settings

from config.network import client_ip


class ProxyTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @override_settings(TRUST_PROXY=False)
    def test_development_ignores_spoofed_client_ip(self):
        request = self.factory.get('/', REMOTE_ADDR='127.0.0.1', HTTP_X_REAL_IP='198.51.100.7')
        self.assertEqual(client_ip(request), '127.0.0.1')

    @override_settings(TRUST_PROXY=True)
    def test_private_proxy_uses_single_validated_address(self):
        request = self.factory.get('/', REMOTE_ADDR='172.20.0.4', HTTP_X_REAL_IP='198.51.100.7')
        self.assertEqual(client_ip(request), '198.51.100.7')

    @override_settings(TRUST_PROXY=True)
    def test_malformed_forwarded_address_does_not_become_client_identity(self):
        request = self.factory.get('/', REMOTE_ADDR='172.20.0.4', HTTP_X_REAL_IP='198.51.100.7, 1.1.1.1')
        self.assertEqual(client_ip(request), '172.20.0.4')

    @override_settings(SECURE_SSL_REDIRECT=True, SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https'))
    def test_forwarded_https_does_not_cause_redirect_loop(self):
        response = self.client.get('/acceso/', HTTP_X_FORWARDED_PROTO='https')
        self.assertEqual(response.status_code, 200)

    @override_settings(SECURE_SSL_REDIRECT=True, SECURE_PROXY_SSL_HEADER=None)
    def test_untrusted_https_header_does_not_bypass_https_redirect(self):
        response = self.client.get('/acceso/', HTTP_X_FORWARDED_PROTO='https')
        self.assertEqual(response.status_code, 301)

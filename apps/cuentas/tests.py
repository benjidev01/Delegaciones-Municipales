from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

from django.contrib.auth.hashers import identify_hasher
from django.db import close_old_connections
from django.test import Client, TestCase, TransactionTestCase, override_settings

from apps.auditoria.models import Evento
from apps.delegaciones.models import Delegacion
from apps.vecinos.forms import VecinoForm
from apps.vecinos.models import Vecino
from .models import Usuario


@override_settings(SECURE_SSL_REDIRECT=False, SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class SeguridadTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.norte = Delegacion.objects.create(nombre='Norte', direccion='Demo')
        cls.sur = Delegacion.objects.create(nombre='Sur', direccion='Demo')
        cls.funcionario = Usuario.objects.create_user('funcionario', password='PruebaSegura-2026', delegacion=cls.norte)
        cls.admin = Usuario.objects.create_superuser('admin', password='AdminSegura-2026', rol='administrador')
        cls.vecino = Vecino.objects.create(delegacion=cls.norte, rut='12345678-5', nombre='Solo Norte', telefono='123', direccion='Demo')

    def setUp(self):
        self.client.force_login(self.funcionario)

    def test_todas_las_vistas_privadas_requieren_sesion(self):
        self.client.logout()
        for route in ['/', '/vecinos/', '/vecinos/nuevo/', '/solicitudes/', '/solicitudes/nueva/',
                      '/agenda/', '/agenda/nueva/', '/reportes/', '/auditoria/']:
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response.url.startswith('/acceso/?next='))

    def test_host_desconocido_rechazado(self):
        response = self.client.get('/', HTTP_HOST='host-no-autorizado.invalid')
        self.assertEqual(response.status_code, 400)

    def test_password_almacenada_como_hash(self):
        self.assertNotEqual(self.funcionario.password, 'PruebaSegura-2026')
        self.assertEqual(identify_hasher(self.funcionario.password).algorithm, 'pbkdf2_sha256')
        self.assertTrue(self.funcionario.check_password('PruebaSegura-2026'))

    def test_cookies_sesion_y_cabeceras(self):
        self.client.logout()
        response = self.client.post('/acceso/', {'username': 'funcionario', 'password': 'PruebaSegura-2026'})
        self.assertEqual(response.status_code, 302)
        cookie = response.cookies['sessionid']
        self.assertTrue(cookie['httponly'])
        self.assertEqual(cookie['samesite'], 'Lax')
        page = self.client.get('/vecinos/')
        self.assertEqual(page['X-Frame-Options'], 'DENY')
        self.assertEqual(page['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(page['Referrer-Policy'], 'same-origin')
        self.assertIn('private', page['Cache-Control'])
        self.assertIn('no-store', page['Cache-Control'])

    @override_settings(DEBUG=False, SESSION_COOKIE_SECURE=True, CSRF_COOKIE_SECURE=True)
    def test_cookies_seguras_configuracion_produccion(self):
        self.client.logout()
        self.client.get('/acceso/', secure=True)
        response = self.client.post('/acceso/', {'username': 'funcionario', 'password': 'PruebaSegura-2026'}, secure=True)
        self.assertTrue(response.cookies['sessionid']['secure'])
        self.assertTrue(self.client.cookies['csrftoken']['secure'])

    def test_csrf_login_obligatorio(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post('/acceso/', {'username': 'funcionario', 'password': 'PruebaSegura-2026'})
        self.assertEqual(response.status_code, 403)

    def test_redireccion_externa_login_rechazada(self):
        self.client.logout()
        response = self.client.post('/acceso/?next=https://externo.invalid/', {'username': 'funcionario', 'password': 'PruebaSegura-2026'})
        self.assertEqual(response.url, '/')

    def test_logout_no_admite_get(self):
        self.assertEqual(self.client.get('/salir/').status_code, 405)
        self.assertEqual(self.client.get('/').status_code, 200)

    def test_cuenta_desactivada_pierde_sesion(self):
        Usuario.objects.filter(pk=self.funcionario.pk).update(is_active=False)
        self.assertEqual(self.client.get('/vecinos/').status_code, 302)

    def test_cambio_delegacion_aplica_en_siguiente_peticion(self):
        self.assertContains(self.client.get('/vecinos/'), 'Solo Norte')
        Usuario.objects.filter(pk=self.funcionario.pk).update(delegacion=self.sur)
        self.assertNotContains(self.client.get('/vecinos/'), 'Solo Norte')

    def test_cambio_rol_restringe_reportes_siguiente_peticion(self):
        Usuario.objects.filter(pk=self.funcionario.pk).update(rol='delegado')
        self.assertEqual(self.client.get('/reportes/').status_code, 200)
        Usuario.objects.filter(pk=self.funcionario.pk).update(rol='funcionario')
        self.assertEqual(self.client.get('/reportes/').status_code, 403)

    def test_password_admin_cambia_e_invalida_sesion_anterior(self):
        self.client.force_login(self.admin)
        old_client = Client()
        old_client.force_login(self.funcionario)
        response = self.client.post(f'/admin/cuentas/usuario/{self.funcionario.pk}/password/', {
            'password1': 'NuevaPruebaRobusta-2026', 'password2': 'NuevaPruebaRobusta-2026', 'usable_password': 'true'})
        self.assertEqual(response.status_code, 302)
        self.funcionario.refresh_from_db()
        self.assertTrue(self.funcionario.check_password('NuevaPruebaRobusta-2026'))
        self.assertEqual(old_client.get('/').status_code, 302)
        self.assertTrue(Evento.objects.filter(accion='usuario.password_cambiada', actor=self.admin,
                                             objeto_id=str(self.funcionario.pk)).exists())

    def test_password_debil_admin_rechazada(self):
        self.client.force_login(self.admin)
        response = self.client.post(f'/admin/cuentas/usuario/{self.funcionario.pk}/password/', {
            'password1': '123', 'password2': '123', 'usable_password': 'true'})
        self.assertEqual(response.status_code, 200)
        self.funcionario.refresh_from_db()
        self.assertTrue(self.funcionario.check_password('PruebaSegura-2026'))
        self.assertFalse(Evento.objects.filter(accion='usuario.password_cambiada').exists())

    def test_funcionario_no_cambia_password_ajena_desde_admin(self):
        response = self.client.post(f'/admin/cuentas/usuario/{self.admin.pk}/password/', {
            'password1': 'IntentoNoAutorizado-2026', 'password2': 'IntentoNoAutorizado-2026'})
        self.assertEqual(response.status_code, 302)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password('AdminSegura-2026'))

    def test_password_ausente_de_auditoria(self):
        self.client.logout()
        self.client.post('/acceso/', {'username': 'nombre-inventado', 'password': 'ValorQueNoSeDebeRegistrar'})
        evento = Evento.objects.get(accion='acceso.fallido')
        self.assertIsNone(evento.actor)
        self.assertEqual(evento.objeto_id, '')
        self.assertNotIn('ValorQueNoSeDebeRegistrar', str(evento.__dict__))
        self.assertNotIn('nombre-inventado', str(evento.__dict__))

    @override_settings(DEBUG=False)
    def test_error_interno_no_revela_detalles(self):
        client = Client(raise_request_exception=False)
        client.force_login(self.funcionario)
        with patch('config.views.crear_solicitud', side_effect=RuntimeError('DetallePrivadoNoMostrar')):
            response = client.post('/solicitudes/nueva/', {'vecino': self.vecino.pk, 'tipo': 'reclamo', 'descripcion': 'Demo'})
        self.assertEqual(response.status_code, 500)
        self.assertNotContains(response, 'DetallePrivadoNoMostrar', status_code=500)
        self.assertContains(response, 'No se pudo completar la operación', status_code=500)

    def test_post_vacio_muestra_errores_requeridos(self):
        response = self.client.post('/vecinos/nuevo/', {})
        self.assertContains(response, 'Este campo es obligatorio')


@override_settings(SECURE_SSL_REDIRECT=False, SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class RegistroConcurrenteTests(TransactionTestCase):
    def test_registro_simultaneo_mismo_rut_muestra_error_controlado(self):
        delegacion = Delegacion.objects.create(nombre='Concurrente', direccion='Demo')
        usuario = Usuario.objects.create_user('concurrente', delegacion=delegacion)
        barrier = Barrier(2)
        original = VecinoForm.is_valid

        def validar(form):
            valid = original(form)
            barrier.wait(timeout=10)
            return valid

        def crear(_):
            close_old_connections()
            try:
                client = Client()
                client.force_login(Usuario.objects.get(pk=usuario.pk))
                response = client.post('/vecinos/nuevo/', {'rut': '12345678-5', 'nombre': 'Vecino concurrente',
                    'telefono': '123', 'direccion': 'Ficticia'})
                if response.status_code == 200:
                    self.assertIn('Este RUT ya está registrado', response.content.decode())
                return response.status_code
            finally:
                close_old_connections()

        with patch.object(VecinoForm, 'is_valid', validar):
            with ThreadPoolExecutor(max_workers=2) as pool:
                responses = list(pool.map(crear, range(2)))
        self.assertCountEqual(responses, [302, 200])
        self.assertEqual(Vecino.objects.count(), 1)
        self.assertEqual(Evento.objects.filter(accion='vecino.creado').count(), 1)


@override_settings(SECURE_SSL_REDIRECT=False, SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class InactividadTests(TestCase):
    def setUp(self):
        delegation = Delegacion.objects.create(nombre='Inactividad', direccion='Demo')
        self.user = Usuario.objects.create_user('idle', password='PruebaSegura-2026', delegacion=delegation)
        self.client.force_login(self.user)

    def timestamp(self, value):
        session = self.client.session
        session['ultima_actividad'] = value
        session.save()

    def test_sesion_inactiva_expira_antes_de_acceder_a_datos(self):
        self.timestamp(1000)
        with patch('config.middleware.time', return_value=2800):
            response = self.client.get('/vecinos/')
        self.assertRedirects(response, '/acceso/', fetch_redirect_response=False)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertTrue(Evento.objects.filter(actor=self.user, accion='acceso.salida').exists())

    def test_actividad_renueva_plazo_y_no_expira_desde_login(self):
        self.timestamp(1000)
        with patch('config.middleware.time', return_value=2700):
            self.assertEqual(self.client.post('/sesion/actividad/').status_code, 200)
        self.assertEqual(self.client.session['ultima_actividad'], 2700)
        with patch('config.middleware.time', return_value=4400):
            self.assertEqual(self.client.get('/vecinos/').status_code, 200)

    def test_heartbeat_no_revive_sesion_expirada(self):
        self.timestamp(1000)
        with patch('config.middleware.time', return_value=2801):
            self.assertEqual(self.client.post('/sesion/actividad/').status_code, 302)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_actividad_requiere_autenticacion_post_y_csrf(self):
        self.assertEqual(self.client.get('/sesion/actividad/').status_code, 405)
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(self.user)
        self.assertEqual(strict.post('/sesion/actividad/').status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.post('/sesion/actividad/').status_code, 302)

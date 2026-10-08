from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from apps.auditoria.models import Evento
from apps.delegaciones.models import Delegacion
from apps.vecinos.forms import VecinoForm
from apps.vecinos.models import Vecino, normalizar_rut
from .models import Solicitud, CambioEstado, Observacion
from .services import crear_solicitud, transicionar, agregar_observacion

@override_settings(SECURE_SSL_REDIRECT=False, SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class SprintTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.norte = Delegacion.objects.create(nombre='Norte', direccion='Demo 1')
        cls.sur = Delegacion.objects.create(nombre='Sur', direccion='Demo 2')
        User = get_user_model()
        cls.funcionario = User.objects.create_user('funcionario', password='PruebaRobusta-2026', delegacion=cls.norte)
        cls.otro = User.objects.create_user('otro', password='PruebaRobusta-2026', delegacion=cls.sur)
        cls.colega = User.objects.create_user('colega', password='PruebaRobusta-2026', delegacion=cls.norte)
        cls.delegado = User.objects.create_user('delegado', password='PruebaRobusta-2026', rol='delegado', delegacion=cls.norte)
        cls.admin = User.objects.create_superuser('administrador', password='PruebaRobusta-2026', rol='administrador')
        cls.vecino = Vecino.objects.create(delegacion=cls.norte, rut='12345678-5', nombre='Vecino Norte', telefono='123456789', direccion='Ficticia 1')
        cls.vecino_sur = Vecino.objects.create(delegacion=cls.sur, rut='12345678-5', nombre='Vecino Sur Secreto', telefono='123456789', direccion='Ficticia 2')

    def setUp(self):
        self.client.force_login(self.funcionario)
        self.solicitud = crear_solicitud(self.funcionario, self.vecino, 'reclamo', 'Revisión de una luminaria.')

    def asignar(self):
        transicionar(self.delegado, self.solicitud.pk, 'ingresada', 'asignada', 'Asignación inicial.', self.funcionario.pk)

    def test_rut_normalizado(self):
        self.assertEqual(normalizar_rut('12.345.678-5'), '12345678-5')
        self.assertEqual(normalizar_rut('1-9'), '1-9')

    def test_rut_invalido(self):
        for rut in ['12345678-9', 'texto', "' OR 1=1", '123', '0-0', '00000000-0']:
            with self.assertRaises(ValidationError):
                normalizar_rut(rut)

    def test_contacto_obligatorio(self):
        self.vecino.telefono = ''
        with self.assertRaises(ValidationError):
            self.vecino.full_clean()

    def test_duplicado_rut_formulario(self):
        form = VecinoForm(data={'delegacion': self.norte.pk, 'rut': '12.345.678-5', 'nombre': 'Duplicado',
                               'telefono': '123', 'direccion': 'Demo'}, usuario=self.funcionario)
        self.assertFalse(form.is_valid())

    def test_duplicado_rut_base_datos(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Vecino.objects.create(delegacion=self.norte, rut='12345678-5', nombre='Duplicado', direccion='Demo')

    def test_delegacion_formulario_no_manipulable(self):
        form = VecinoForm(data={'delegacion': self.sur.pk, 'rut': '11.111.111-1', 'nombre': 'Nuevo',
                               'telefono': '123', 'direccion': 'Demo'}, usuario=self.funcionario)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['delegacion'], self.norte)

    def test_usuario_sin_delegacion_invalido(self):
        usuario = get_user_model()(username='sin-delegacion', rol='funcionario')
        with self.assertRaises(ValidationError):
            usuario.full_clean()
        self.assertFalse(usuario.scope(Vecino.objects.all()).exists())

    def test_ciclo_completo(self):
        self.asignar()
        transicionar(self.funcionario, self.solicitud.pk, 'asignada', 'atencion', 'Se inicia la revisión.')
        transicionar(self.funcionario, self.solicitud.pk, 'atencion', 'resuelta', 'Luminaria reparada.')
        transicionar(self.delegado, self.solicitud.pk, 'resuelta', 'cerrada', 'Solución verificada.')
        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.estado, 'cerrada')
        self.assertEqual(self.solicitud.cambios.count(), 4)
        self.assertEqual(self.solicitud.observaciones.count(), 4)
        self.assertEqual(Evento.objects.filter(entidad='solicitudes.Solicitud', objeto_id=str(self.solicitud.pk)).count(), 5)

    def test_funcionario_no_asigna(self):
        with self.assertRaises(PermissionDenied):
            transicionar(self.funcionario, self.solicitud.pk, 'ingresada', 'asignada', 'Asignar', self.funcionario.pk)

    def test_responsable_otra_delegacion_rechazado(self):
        with self.assertRaises(ValidationError):
            transicionar(self.delegado, self.solicitud.pk, 'ingresada', 'asignada', 'Asignar', self.otro.pk)

    def test_responsable_inactivo_rechazado(self):
        self.funcionario.is_active = False
        self.funcionario.save()
        with self.assertRaises(ValidationError):
            transicionar(self.delegado, self.solicitud.pk, 'ingresada', 'asignada', 'Asignar', self.funcionario.pk)

    def test_solo_responsable_inicia_atencion(self):
        self.asignar()
        with self.assertRaises(PermissionDenied):
            transicionar(self.colega, self.solicitud.pk, 'asignada', 'atencion', 'Inicio')

    def test_saltos_de_estado_rechazados(self):
        with self.assertRaises(ValidationError):
            transicionar(self.delegado, self.solicitud.pk, 'ingresada', 'cerrada', 'Salto')

    def test_estado_desactualizado_rechazado(self):
        self.asignar()
        with self.assertRaises(ValidationError):
            transicionar(self.delegado, self.solicitud.pk, 'ingresada', 'asignada', 'Repetición', self.funcionario.pk)
        self.assertEqual(CambioEstado.objects.count(), 1)

    def test_motivo_obligatorio(self):
        with self.assertRaises(ValidationError):
            transicionar(self.delegado, self.solicitud.pk, 'ingresada', 'asignada', '  ', self.funcionario.pk)

    def test_fallo_auditoria_revierte_estado_e_historial(self):
        with patch('apps.solicitudes.services.auditar', side_effect=RuntimeError('Fallo simulado')):
            with self.assertRaises(RuntimeError):
                self.asignar()
        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.estado, 'ingresada')
        self.assertEqual(CambioEstado.objects.count(), 0)
        self.assertEqual(Observacion.objects.count(), 0)

    def test_no_crear_solicitud_otra_delegacion(self):
        with self.assertRaises(PermissionDenied):
            crear_solicitud(self.funcionario, self.vecino_sur, 'reclamo', 'Intento')

    def test_listados_no_revelan_otra_delegacion(self):
        crear_solicitud(self.otro, self.vecino_sur, 'reclamo', 'Solicitud sur')
        for url in ['/', '/vecinos/', '/solicitudes/']:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, 'Vecino Sur Secreto')

    def test_objetos_ajenos_no_accesibles(self):
        ajena = crear_solicitud(self.otro, self.vecino_sur, 'reclamo', 'Solicitud sur')
        for url in [f'/solicitudes/{ajena.pk}/', f'/vecinos/{self.vecino_sur.pk}/editar/']:
            self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post(f'/solicitudes/{ajena.pk}/observacion/', {'texto': 'Intento'}).status_code, 404)

    def test_vecino_ajeno_no_seleccionable(self):
        response = self.client.post('/solicitudes/nueva/', {'vecino': self.vecino_sur.pk, 'tipo': 'reclamo', 'descripcion': 'Intento'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Solicitud.objects.count(), 1)

    def test_csrf_obligatorio(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.funcionario)
        self.assertEqual(client.post('/solicitudes/nueva/', {'vecino': self.vecino.pk}).status_code, 403)

    def test_xss_escapado(self):
        self.solicitud.descripcion = '<script>alert(1)</script>'
        self.solicitud.save()
        response = self.client.get(reverse('solicitud_detalle', args=[self.solicitud.pk]))
        self.assertNotContains(response, '<script>alert(1)</script>')
        self.assertContains(response, '&lt;script&gt;alert(1)&lt;/script&gt;')

    def test_busqueda_inyeccion_sin_efecto(self):
        response = self.client.get('/vecinos/', {'q': "' OR 1=1 --"})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Vecino Sur Secreto')
        self.assertEqual(Vecino.objects.count(), 2)

    def test_auditoria_solo_administrador(self):
        self.assertEqual(self.client.get('/auditoria/').status_code, 403)
        self.client.force_login(self.delegado)
        self.assertEqual(self.client.get('/auditoria/').status_code, 403)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get('/auditoria/').status_code, 200)

    def test_administrador_ve_todas_delegaciones(self):
        self.client.force_login(self.admin)
        self.assertContains(self.client.get('/vecinos/'), 'Vecino Sur Secreto')

    def test_delegacion_inactiva_denegada(self):
        self.norte.activa = False
        self.norte.save()
        self.assertEqual(self.client.get(f'/solicitudes/{self.solicitud.pk}/').status_code, 404)
        with self.assertRaises(PermissionDenied):
            agregar_observacion(self.funcionario, self.solicitud.pk, 'Intento')

    def test_solicitud_cerrada_sin_observaciones_nuevas(self):
        self.solicitud.estado = 'cerrada'
        self.solicitud.save()
        with self.assertRaises(ValidationError):
            agregar_observacion(self.funcionario, self.solicitud.pk, 'Intento')

    def test_funcionario_no_cierra(self):
        self.solicitud.estado = 'resuelta'
        self.solicitud.save()
        with self.assertRaises(PermissionDenied):
            transicionar(self.funcionario, self.solicitud.pk, 'resuelta', 'cerrada', 'Intento')

    def test_observacion_auditada(self):
        agregar_observacion(self.funcionario, self.solicitud.pk, 'Seguimiento')
        self.assertEqual(Observacion.objects.count(), 1)
        self.assertTrue(Evento.objects.filter(accion='observacion.creada').exists())

    def test_endpoints_mutacion_solo_post(self):
        self.assertEqual(self.client.get(f'/solicitudes/{self.solicitud.pk}/estado/').status_code, 405)
        self.assertEqual(self.client.get(f'/solicitudes/{self.solicitud.pk}/observacion/').status_code, 405)

    def test_login_logout_y_auditoria(self):
        self.client.logout()
        response = self.client.post('/acceso/', {'username': 'funcionario', 'password': 'PruebaRobusta-2026'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get('/').status_code, 200)
        self.assertTrue(Evento.objects.filter(accion='acceso.exitoso', actor=self.funcionario).exists())
        self.assertEqual(self.client.post('/salir/').status_code, 302)
        self.assertEqual(self.client.get('/').status_code, 302)

    def test_login_erroneo_y_limite(self):
        self.client.logout()
        for attempt in range(4):
            response = self.client.post('/acceso/', {'username': 'funcionario', 'password': 'Incorrecta'})
            self.assertEqual(response.status_code, 200)
        response = self.client.post('/acceso/', {'username': 'funcionario', 'password': 'Incorrecta'})
        self.assertEqual(response.status_code, 429)
        response = self.client.post('/acceso/', {'username': 'funcionario', 'password': 'PruebaRobusta-2026'})
        self.assertEqual(response.status_code, 429)
        self.assertEqual(Evento.objects.filter(accion='acceso.fallido').count(), 6)

    def test_admin_sin_modificacion_auditoria(self):
        self.client.force_login(self.admin)
        evento = Evento.objects.first()
        response = self.client.post(f'/admin/auditoria/evento/{evento.pk}/change/', {'accion': 'manipulada'})
        self.assertEqual(response.status_code, 403)
        evento.refresh_from_db()
        self.assertNotEqual(evento.accion, 'manipulada')

    def test_staff_delegado_no_entra_admin(self):
        self.delegado.is_staff = True
        self.delegado.save()
        self.client.force_login(self.delegado)
        self.assertEqual(self.client.get('/admin/').status_code, 302)

    def test_error_transicion_conserva_datos(self):
        self.client.force_login(self.delegado)
        response = self.client.post(f'/solicitudes/{self.solicitud.pk}/estado/', {
            'esperado': 'ingresada', 'nuevo': 'asignada', 'motivo': 'Conservar este texto', 'responsable': ''})
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, 'Conservar este texto', status_code=400)

    def test_edicion_vecino_no_transfiere_delegacion(self):
        form = VecinoForm(instance=self.vecino, usuario=self.admin, data={
            'delegacion': self.sur.pk, 'rut': self.vecino.rut, 'nombre': self.vecino.nombre,
            'telefono': self.vecino.telefono, 'direccion': self.vecino.direccion})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['delegacion'], self.norte)

    def test_responsable_no_cambia_delegacion_con_pendientes(self):
        self.asignar()
        self.funcionario.delegacion = self.sur
        with self.assertRaises(ValidationError):
            self.funcionario.full_clean()

class ConcurrenciaTests(TransactionTestCase):
    def test_asignaciones_simultaneas_solo_una_confirmada(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.db import close_old_connections
        delegacion = Delegacion.objects.create(nombre='Concurrente', direccion='Demo')
        usuario = get_user_model().objects.create(username='delegado.concurrente', rol='delegado', delegacion=delegacion)
        vecino = Vecino.objects.create(delegacion=delegacion, rut='12345678-5', nombre='Demo', telefono='123', direccion='Demo')
        solicitud = crear_solicitud(usuario, vecino, 'reclamo', 'Prueba de concurrencia')
        barrier = Barrier(2)

        def intentar():
            close_old_connections()
            try:
                actor = get_user_model().objects.get(pk=usuario.pk)
                barrier.wait(timeout=10)
                try:
                    transicionar(actor, solicitud.pk, 'ingresada', 'asignada', 'Asignación simultánea', actor.pk)
                    return 'confirmada'
                except ValidationError:
                    return 'conflicto'
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            resultados = list(pool.map(lambda _: intentar(), range(2)))
        self.assertCountEqual(resultados, ['confirmada', 'conflicto'])
        self.assertEqual(CambioEstado.objects.filter(solicitud=solicitud).count(), 1)
        self.assertEqual(Observacion.objects.filter(solicitud=solicitud).count(), 1)

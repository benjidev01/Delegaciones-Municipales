from datetime import datetime
from zoneinfo import ZoneInfo

from django.test import TestCase, override_settings

from apps.cuentas.models import Usuario
from apps.delegaciones.models import Delegacion
from apps.solicitudes.models import Solicitud
from apps.solicitudes.services import crear_solicitud
from apps.vecinos.models import Vecino


@override_settings(SECURE_SSL_REDIRECT=False, SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class ReportesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.norte = Delegacion.objects.create(nombre='Norte', direccion='Demo')
        cls.sur = Delegacion.objects.create(nombre='Sur', direccion='Demo')
        cls.funcionario = Usuario.objects.create_user('funcionario', delegacion=cls.norte)
        cls.otro = Usuario.objects.create_user('otro', delegacion=cls.sur)
        cls.delegado = Usuario.objects.create_user('delegado', rol='delegado', delegacion=cls.norte)
        cls.admin = Usuario.objects.create_superuser('admin', rol='administrador')
        norte = Vecino.objects.create(delegacion=cls.norte, rut='12345678-5', nombre='Vecino Norte', telefono='123', direccion='Demo')
        sur = Vecino.objects.create(delegacion=cls.sur, rut='12345678-5', nombre='Vecino Sur Confidencial', telefono='123', direccion='Demo')
        cls.una = crear_solicitud(cls.funcionario, norte, 'reclamo', 'Primera')
        cls.dos = crear_solicitud(cls.funcionario, norte, 'permiso', 'Segunda')
        cls.tres = crear_solicitud(cls.funcionario, norte, 'otro', 'Tercera')
        cls.ajena = crear_solicitud(cls.otro, sur, 'otro', 'Sur')
        zone = ZoneInfo('America/Santiago')
        for solicitud, fecha, estado in [
            (cls.una, datetime(2026, 10, 7, 0, 0, tzinfo=zone), 'ingresada'),
            (cls.dos, datetime(2026, 10, 8, 23, 59, 59, tzinfo=zone), 'cerrada'),
            (cls.tres, datetime(2026, 10, 9, 0, 0, tzinfo=zone), 'ingresada'),
            (cls.ajena, datetime(2026, 10, 8, 12, 0, tzinfo=zone), 'ingresada'),
        ]:
            Solicitud.objects.filter(pk=solicitud.pk).update(creada_en=fecha, estado=estado)

    def setUp(self):
        self.client.force_login(self.delegado)

    def test_funcionario_sin_acceso(self):
        self.client.force_login(self.funcionario)
        self.assertEqual(self.client.get('/reportes/').status_code, 403)

    def test_delegado_solo_su_ambito(self):
        response = self.client.get('/reportes/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total'], 3)
        self.assertNotContains(response, 'Vecino Sur Confidencial')
        self.assertEqual(len(response.context['por_delegacion']), 1)

    def test_administrador_ambas_delegaciones(self):
        self.client.force_login(self.admin)
        response = self.client.get('/reportes/')
        self.assertEqual(response.context['total'], 4)
        self.assertContains(response, 'Vecino Sur Confidencial')
        self.assertEqual(len(response.context['por_delegacion']), 2)

    def test_periodo_inclusivo_en_horario_chile(self):
        response = self.client.get('/reportes/', {'desde': '2026-10-07', 'hasta': '2026-10-08'})
        self.assertEqual(response.context['total'], 2)
        self.assertCountEqual([s.pk for s in response.context['pagina']], [self.una.pk, self.dos.pk])

    def test_filtro_por_un_solo_dia(self):
        response = self.client.get('/reportes/', {'desde': '2026-10-08', 'hasta': '2026-10-08'})
        self.assertEqual(response.context['total'], 1)
        self.assertEqual(response.context['pagina'][0].pk, self.dos.pk)

    def test_filtro_estado(self):
        response = self.client.get('/reportes/', {'estado': 'cerrada'})
        self.assertEqual(response.context['total'], 1)

    def test_filtro_delegacion_administrador(self):
        self.client.force_login(self.admin)
        response = self.client.get('/reportes/', {'delegacion': self.sur.pk})
        self.assertEqual(response.context['total'], 1)
        self.assertEqual(response.context['pagina'][0].pk, self.ajena.pk)

    def test_delegacion_ajena_rechazada_sin_ampliar_reporte(self):
        response = self.client.get('/reportes/', {'delegacion': self.sur.pk})
        self.assertEqual(response.context['total'], 0)
        self.assertTrue(response.context['filtros'].errors)
        self.assertNotContains(response, 'Vecino Sur Confidencial')

    def test_periodo_invertido_rechazado(self):
        response = self.client.get('/reportes/', {'desde': '2026-10-09', 'hasta': '2026-10-07'})
        self.assertEqual(response.context['total'], 0)
        self.assertContains(response, 'fecha final debe ser igual o posterior')

    def test_fecha_y_estado_invalidos_rechazados(self):
        for filtros in [{'desde': 'no-fecha'}, {'estado': 'inventado'}, {'delegacion': "' OR 1=1"}]:
            response = self.client.get('/reportes/', filtros)
            self.assertEqual(response.context['total'], 0)
            self.assertTrue(response.context['filtros'].errors)

    def test_agregados_coinciden_con_total(self):
        response = self.client.get('/reportes/')
        self.assertEqual(sum(s['total'] for s in response.context['por_estado']), response.context['total'])
        self.assertEqual(sum(s['total'] for s in response.context['por_delegacion']), response.context['total'])

    def test_delegacion_inactiva_no_incluida(self):
        self.norte.activa = False
        self.norte.save()
        self.assertEqual(self.client.get('/reportes/').context['total'], 0)

    def test_filtros_combinados(self):
        response = self.client.get('/reportes/', {'desde': '2026-10-07', 'hasta': '2026-10-08', 'estado': 'cerrada', 'delegacion': self.norte.pk})
        self.assertEqual(response.context['total'], 1)
        self.assertEqual(response.context['pagina'][0].pk, self.dos.pk)

    def test_navegacion_reportes_segun_rol(self):
        self.assertContains(self.client.get('/'), 'href="/reportes/"')
        self.client.force_login(self.funcionario)
        self.assertNotContains(self.client.get('/'), 'href="/reportes/"')

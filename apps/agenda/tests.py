from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from unittest.mock import patch

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, close_old_connections, transaction
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.utils import timezone

from apps.auditoria.models import Evento
from apps.cuentas.models import Usuario
from apps.delegaciones.models import Delegacion
from apps.solicitudes.services import crear_solicitud
from apps.vecinos.models import Vecino
from .forms import CitaForm
from .models import Cita, CambioCita
from .services import reservar, cambiar_estado


class DatosAgenda:
    @classmethod
    def setUpTestData(cls):
        cls.norte = Delegacion.objects.create(nombre='Norte', direccion='Demo')
        cls.sur = Delegacion.objects.create(nombre='Sur', direccion='Demo')
        cls.funcionario = Usuario.objects.create_user('funcionario', delegacion=cls.norte)
        cls.colega = Usuario.objects.create_user('colega', delegacion=cls.norte)
        cls.otro = Usuario.objects.create_user('otro', delegacion=cls.sur)
        cls.delegado = Usuario.objects.create_user('delegado', rol='delegado', delegacion=cls.norte)
        cls.admin = Usuario.objects.create_superuser('admin', rol='administrador')
        cls.vecino = Vecino.objects.create(delegacion=cls.norte, rut='12345678-5', nombre='Vecino Norte', telefono='123', direccion='Demo')
        cls.vecino_sur = Vecino.objects.create(delegacion=cls.sur, rut='12345678-5', nombre='Vecino Sur Confidencial', telefono='123', direccion='Demo')

    def datos(self, **overrides):
        data = {'usuario': self.funcionario, 'vecino': self.vecino, 'funcionario': self.funcionario,
                'inicio': (timezone.now() + timedelta(days=2)).replace(second=0, microsecond=0),
                'duracion': 30, 'motivo': 'Atención ficticia'}
        data.update(overrides)
        return data


@override_settings(SECURE_SSL_REDIRECT=False, SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class AgendaTests(DatosAgenda, TestCase):
    def setUp(self):
        self.client.force_login(self.funcionario)

    def test_reserva_valida_auditada(self):
        cita = reservar(**self.datos())
        self.assertEqual(cita.estado, 'programada')
        self.assertEqual(cita.fin - cita.inicio, timedelta(minutes=30))
        self.assertTrue(Evento.objects.filter(accion='cita.reservada', objeto_id=str(cita.pk)).exists())

    def test_reserva_pasada_denegada(self):
        with self.assertRaises(ValidationError):
            reservar(**self.datos(inicio=timezone.now() - timedelta(minutes=1)))

    def test_fecha_sin_zona_denegada(self):
        with self.assertRaises(ValidationError):
            reservar(**self.datos(inicio=timezone.now().replace(tzinfo=None) + timedelta(days=2)))

    def test_duracion_no_permitida(self):
        for value in (0, -30, 200, 31):
            with self.assertRaises(ValidationError):
                reservar(**self.datos(duracion=value))

    def test_vecino_otra_delegacion_denegado(self):
        with self.assertRaises(PermissionDenied):
            reservar(**self.datos(vecino=self.vecino_sur, funcionario=self.otro))

    def test_funcionario_otra_delegacion_denegado(self):
        with self.assertRaises(ValidationError):
            reservar(**self.datos(funcionario=self.otro))

    def test_funcionario_inactivo_denegado(self):
        self.funcionario.is_active = False
        self.funcionario.save()
        with self.assertRaises(ValidationError):
            reservar(**self.datos(usuario=self.delegado))

    def test_delegado_no_seleccionable_como_funcionario(self):
        with self.assertRaises(ValidationError):
            reservar(**self.datos(funcionario=self.delegado))

    def test_solicitud_de_otro_vecino_denegada(self):
        otro_vecino = Vecino.objects.create(delegacion=self.norte, rut='11111111-1', nombre='Otro vecino', telefono='123', direccion='Demo')
        solicitud = crear_solicitud(self.funcionario, otro_vecino, 'reclamo', 'Demo')
        with self.assertRaises(ValidationError):
            reservar(**self.datos(solicitud=solicitud))

    def test_solicitud_correcta_vinculada(self):
        solicitud = crear_solicitud(self.funcionario, self.vecino, 'reclamo', 'Demo')
        cita = reservar(**self.datos(solicitud=solicitud))
        self.assertEqual(cita.solicitud, solicitud)

    def test_solicitud_cerrada_denegada(self):
        solicitud = crear_solicitud(self.funcionario, self.vecino, 'reclamo', 'Demo')
        solicitud.estado = 'cerrada'
        solicitud.save()
        with self.assertRaises(ValidationError):
            reservar(**self.datos(solicitud=solicitud))

    def test_superposiciones_denegadas(self):
        cita = reservar(**self.datos())
        for inicio in [cita.inicio, cita.inicio + timedelta(minutes=15), cita.inicio - timedelta(minutes=15)]:
            with self.assertRaises(ValidationError):
                reservar(**self.datos(inicio=inicio))
        self.assertEqual(Cita.objects.count(), 1)

    def test_horarios_adyacentes_permitidos(self):
        cita = reservar(**self.datos())
        reservar(**self.datos(inicio=cita.fin))
        reservar(**self.datos(inicio=cita.inicio - timedelta(minutes=30)))
        self.assertEqual(Cita.objects.count(), 3)

    def test_distintos_funcionarios_mismo_horario(self):
        cita = reservar(**self.datos())
        reservar(**self.datos(funcionario=self.colega, inicio=cita.inicio))
        self.assertEqual(Cita.objects.count(), 2)

    def test_exclusion_postgres_impide_escritura_directa(self):
        cita = reservar(**self.datos())
        with self.assertRaises(IntegrityError), transaction.atomic():
            Cita.objects.create(delegacion=self.norte, vecino=self.vecino, funcionario=self.funcionario,
                                creador=self.funcionario, inicio=cita.inicio, fin=cita.fin, motivo='Bypass')

    def test_constraint_fin_posterior(self):
        inicio = timezone.now() + timedelta(days=2)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Cita.objects.create(delegacion=self.norte, vecino=self.vecino, funcionario=self.funcionario,
                                creador=self.funcionario, inicio=inicio, fin=inicio, motivo='Fin inválido')

    def test_cancelar_libera_horario_y_guarda_historial(self):
        cita = reservar(**self.datos())
        cambiar_estado(self.funcionario, cita.pk, 'programada', 'cancelada', 'Vecino cancela')
        nueva = reservar(**self.datos(inicio=cita.inicio))
        self.assertNotEqual(nueva.pk, cita.pk)
        self.assertEqual(CambioCita.objects.get(cita=cita).nuevo, 'cancelada')
        self.assertTrue(Evento.objects.filter(accion='cita.cancelada').exists())

    def test_no_atender_antes_de_inicio(self):
        cita = reservar(**self.datos())
        with self.assertRaises(ValidationError):
            cambiar_estado(self.funcionario, cita.pk, 'programada', 'atendida', 'Adelantar')

    def test_atendida_por_funcionario_responsable(self):
        cita = reservar(**self.datos())
        with patch('apps.agenda.services.timezone.now', return_value=cita.inicio + timedelta(minutes=5)):
            cambiar_estado(self.funcionario, cita.pk, 'programada', 'atendida', 'Atención completada')
        cita.refresh_from_db()
        self.assertEqual(cita.estado, 'atendida')
        self.assertEqual(cita.cambios.count(), 1)

    def test_colega_no_marca_atendida(self):
        cita = reservar(**self.datos())
        with patch('apps.agenda.services.timezone.now', return_value=cita.fin):
            with self.assertRaises(PermissionDenied):
                cambiar_estado(self.colega, cita.pk, 'programada', 'atendida', 'No autorizado')

    def test_cambio_desactualizado_o_terminal_denegado(self):
        cita = reservar(**self.datos())
        cambiar_estado(self.funcionario, cita.pk, 'programada', 'cancelada', 'Cancelación')
        with self.assertRaises(ValidationError):
            cambiar_estado(self.funcionario, cita.pk, 'programada', 'atendida', 'Repetido')
        self.assertEqual(cita.cambios.count(), 1)

    def test_motivo_de_cancelacion_obligatorio(self):
        cita = reservar(**self.datos())
        with self.assertRaises(ValidationError):
            cambiar_estado(self.funcionario, cita.pk, 'programada', 'cancelada', '  ')

    def test_fallo_auditoria_revierte_reserva(self):
        with patch('apps.agenda.services.auditar', side_effect=RuntimeError('Simulado')):
            with self.assertRaises(RuntimeError):
                reservar(**self.datos())
        self.assertFalse(Cita.objects.exists())

    def test_fallo_auditoria_revierte_cancelacion(self):
        cita = reservar(**self.datos())
        with patch('apps.agenda.services.auditar', side_effect=RuntimeError('Simulado')):
            with self.assertRaises(RuntimeError):
                cambiar_estado(self.funcionario, cita.pk, 'programada', 'cancelada', 'Cancelación')
        cita.refresh_from_db()
        self.assertEqual(cita.estado, 'programada')
        self.assertEqual(cita.cambios.count(), 0)

    def test_citas_ajenas_no_visibles(self):
        cita = reservar(**self.datos(usuario=self.otro, vecino=self.vecino_sur, funcionario=self.otro))
        self.assertNotContains(self.client.get('/agenda/'), self.vecino_sur.nombre)
        self.assertEqual(self.client.get(f'/agenda/{cita.pk}/').status_code, 404)
        self.assertEqual(self.client.post(f'/agenda/{cita.pk}/estado/', {'nuevo': 'cancelada'}).status_code, 404)

    def test_formulario_filtra_objetos_ajenos(self):
        form = CitaForm(usuario=self.funcionario)
        self.assertNotIn(self.vecino_sur, form.fields['vecino'].queryset)
        self.assertNotIn(self.otro, form.fields['funcionario'].queryset)

    def test_fecha_invalida_no_amplia_listado(self):
        reservar(**self.datos())
        response = self.client.get('/agenda/', {'fecha': 'no-es-fecha'})
        self.assertContains(response, 'Introduzca una fecha válida')
        self.assertEqual(len(response.context['pagina']), 0)

    def test_fecha_y_estado_filtran(self):
        cita = reservar(**self.datos())
        reservar(**self.datos(inicio=cita.inicio + timedelta(days=1)))
        date = timezone.localtime(cita.inicio).date().isoformat()
        self.assertEqual(len(self.client.get('/agenda/', {'fecha': date}).context['pagina']), 1)
        self.assertEqual(len(self.client.get('/agenda/', {'estado': 'cancelada'}).context['pagina']), 0)

    def test_csrf_y_metodo_http(self):
        cita = reservar(**self.datos())
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.funcionario)
        self.assertEqual(client.post('/agenda/nueva/', {}).status_code, 403)
        self.assertEqual(self.client.get(f'/agenda/{cita.pk}/estado/').status_code, 405)

    def test_historial_escapa_xss(self):
        cita = reservar(**self.datos(motivo='<script>alert(1)</script>'))
        response = self.client.get(f'/agenda/{cita.pk}/')
        self.assertNotContains(response, '<script>alert(1)</script>')
        self.assertContains(response, '&lt;script&gt;alert(1)&lt;/script&gt;')

    def test_rol_y_delegacion_con_citas_pendientes(self):
        reservar(**self.datos())
        self.funcionario.delegacion = self.sur
        with self.assertRaises(ValidationError):
            self.funcionario.full_clean()
        self.funcionario.delegacion = self.norte
        self.funcionario.rol = 'delegado'
        with self.assertRaises(ValidationError):
            self.funcionario.full_clean()

    def test_no_desactivar_funcionario_con_citas_pendientes(self):
        reservar(**self.datos())
        self.funcionario.is_active = False
        with self.assertRaises(ValidationError):
            self.funcionario.full_clean()

    def test_hora_inexistente_cambio_estacional_rechazada(self):
        form = CitaForm(usuario=self.funcionario, data={'vecino': self.vecino.pk,
            'funcionario': self.funcionario.pk, 'inicio': '2027-09-05T00:30',
            'duracion': 30, 'motivo': 'Hora inexistente en Chile'})
        self.assertFalse(form.is_valid())
        self.assertIn('inicio', form.errors)

    def test_reserva_desde_formulario(self):
        data = self.datos()
        response = self.client.post('/agenda/nueva/', {
            'vecino': self.vecino.pk, 'funcionario': self.funcionario.pk, 'solicitud': '',
            'inicio': timezone.localtime(data['inicio']).strftime('%Y-%m-%dT%H:%M'),
            'duracion': 30, 'motivo': data['motivo']})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Cita.objects.count(), 1)

    def test_superposicion_formulario_conserva_motivo(self):
        cita = reservar(**self.datos())
        response = self.client.post('/agenda/nueva/', {
            'vecino': self.vecino.pk, 'funcionario': self.funcionario.pk, 'solicitud': '',
            'inicio': timezone.localtime(cita.inicio).strftime('%Y-%m-%dT%H:%M'),
            'duracion': 30, 'motivo': 'Conservar este motivo'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ya tiene una atención')
        self.assertContains(response, 'Conservar este motivo')


class AgendaConcurrenciaTests(TransactionTestCase):
    def test_reservas_simultaneas_solo_una_confirmada(self):
        delegacion = Delegacion.objects.create(nombre='Concurrente', direccion='Demo')
        funcionario = Usuario.objects.create(username='concurrente', delegacion=delegacion)
        vecino = Vecino.objects.create(delegacion=delegacion, rut='12345678-5', nombre='Demo', telefono='123', direccion='Demo')
        inicio = timezone.now() + timedelta(days=2)
        barrier = Barrier(2)

        def intentar(_):
            close_old_connections()
            try:
                actor = Usuario.objects.get(pk=funcionario.pk)
                persona = Vecino.objects.get(pk=vecino.pk)
                barrier.wait(timeout=10)
                try:
                    reservar(actor, persona, actor, inicio, 30, 'Simultánea')
                    return 'confirmada'
                except ValidationError:
                    return 'conflicto'
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(intentar, range(2)))
        self.assertCountEqual(results, ['confirmada', 'conflicto'])
        self.assertEqual(Cita.objects.count(), 1)
        self.assertEqual(Evento.objects.filter(accion='cita.reservada').count(), 1)

# Código completo para revisión

Código propio completo, pruebas, migraciones y configuración pública. Sin credenciales ni binarios de terceros.


## .dockerignore

````
.git
.venv
.local
**/__pycache__
**/*.pyc
staticfiles
.env
.env.*
**/*.pem
**/*.key
**/*.crt
.coverage
dist
docs/evidencias
attachments

````


## .gitignore

````
.venv/
__pycache__/
*.pyc
.local/
staticfiles/
.coverage
.env
.env.*
*.pem
*.key
*.crt
*.sqlite3
*.dump
*.log
vendor/wheels/
dist/

````


## Dockerfile

````
FROM python:3.12-slim-bookworm@sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.lock ./
COPY vendor/ /vendor/
RUN if [ -d /vendor/wheels ]; then \
      python -m pip install --no-cache-dir --no-index --find-links=/vendor/wheels --require-hashes -r requirements.lock; \
    else \
      python -m pip install --no-cache-dir --require-hashes -r requirements.lock; \
    fi \
    && useradd --create-home --uid 10001 app
COPY --chown=app:app . /app
RUN mkdir -p /app/.local && chown app:app /app/.local && chmod 700 /app/.local
USER app
EXPOSE 8000
CMD ["sh", "scripts/start_container.sh"]

````


## Dockerfile.ec2

````
FROM python:3.12-slim-bookworm@sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements-prod.lock ./
COPY vendor/ /vendor/
RUN if [ -d /vendor/wheels ]; then \
      python -m pip install --no-cache-dir --no-index --find-links=/vendor/wheels --require-hashes -r requirements-prod.lock; \
    else \
      python -m pip install --no-cache-dir --require-hashes -r requirements-prod.lock; \
    fi \
    && useradd --create-home --uid 10001 app
COPY --chown=app:app . /app
RUN mkdir -p /app/.local /app/staticfiles /run/db-admin \
    && chown app:app /app/.local /app/staticfiles /run/db-admin \
    && chmod 700 /app/.local /run/db-admin
USER app
EXPOSE 8000
CMD ["sh", "scripts/start_ec2.sh"]

````


## apps/__init__.py

````

````


## apps/agenda/__init__.py

````

````


## apps/agenda/forms.py

````
from django import forms
from django.utils import timezone

from apps.cuentas.models import Usuario
from apps.solicitudes.models import Solicitud
from apps.vecinos.models import Vecino
from .models import Cita


class CitaForm(forms.Form):
    vecino = forms.ModelChoiceField(queryset=Vecino.objects.none())
    funcionario = forms.ModelChoiceField(queryset=Usuario.objects.none(), label='Funcionario de atención')
    solicitud = forms.ModelChoiceField(queryset=Solicitud.objects.none(), required=False, label='Solicitud relacionada')
    inicio = forms.DateTimeField(label='Fecha y hora de inicio (Chile)', input_formats=['%Y-%m-%dT%H:%M'],
                                 widget=forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local'}),
                                 help_text='Horario de America/Santiago. No se aceptan fechas pasadas.')
    duracion = forms.TypedChoiceField(label='Duración', coerce=int, initial=30,
                                     choices=[(n, f'{n} minutos') for n in (15, 30, 45, 60)])
    motivo = forms.CharField(label='Motivo de atención', max_length=300, strip=True, widget=forms.Textarea)

    def __init__(self, *args, usuario, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['vecino'].queryset = usuario.scope(Vecino.objects.select_related('delegacion'))
        funcionarios = Usuario.objects.filter(is_active=True, rol='funcionario', delegacion__activa=True)
        if not usuario.administra:
            funcionarios = funcionarios.filter(delegacion_id=usuario.delegacion_id)
        self.fields['funcionario'].queryset = funcionarios.order_by('username')
        self.fields['solicitud'].queryset = usuario.scope(Solicitud.objects.exclude(estado='cerrada'))
        self.fields['solicitud'].label_from_instance = lambda s: f'#{s.pk} · {s.vecino.nombre} · {s.get_tipo_display()}'

    def clean_inicio(self):
        value = self.cleaned_data['inicio']
        if value <= timezone.now():
            raise forms.ValidationError('Seleccione una fecha y hora futuras.')
        return value


class AgendaFiltroForm(forms.Form):
    fecha = forms.DateField(label='Fecha de atención', required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    estado = forms.ChoiceField(required=False, choices=[('', 'Todos los estados')] + Cita.Estado.choices)


class CambioCitaForm(forms.Form):
    esperado = forms.ChoiceField(choices=Cita.Estado.choices, widget=forms.HiddenInput,
                                 initial=Cita.Estado.PROGRAMADA)
    nuevo = forms.ChoiceField(choices=[(Cita.Estado.CANCELADA, 'Cancelar cita'),
                                     (Cita.Estado.ATENDIDA, 'Marcar atendida')], label='Acción')
    motivo = forms.CharField(label='Motivo / resultado de la atención', max_length=1000, strip=True, widget=forms.Textarea)

    def __init__(self, *args, usuario, cita, **kwargs):
        super().__init__(*args, **kwargs)
        if usuario.pk != cita.funcionario_id and not usuario.supervisa:
            self.fields['nuevo'].choices = [(Cita.Estado.CANCELADA, 'Cancelar cita')]

````


## apps/agenda/migrations/0001_initial.py

````
# Generated by Django 5.2.18 on 2026-10-07 21:24

import django.contrib.postgres.constraints
from django.contrib.postgres.operations import BtreeGistExtension
import django.contrib.postgres.fields.ranges
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('delegaciones', '0001_initial'),
        ('solicitudes', '0001_initial'),
        ('vecinos', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        BtreeGistExtension(),
        migrations.CreateModel(
            name='Cita',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('inicio', models.DateTimeField()),
                ('fin', models.DateTimeField()),
                ('estado', models.CharField(choices=[('programada', 'Programada'), ('atendida', 'Atendida'), ('cancelada', 'Cancelada')], default='programada', max_length=12)),
                ('motivo', models.CharField(max_length=300)),
                ('creada_en', models.DateTimeField(auto_now_add=True)),
                ('actualizada_en', models.DateTimeField(auto_now=True)),
                ('creador', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='citas_creadas', to=settings.AUTH_USER_MODEL)),
                ('delegacion', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='delegaciones.delegacion')),
                ('funcionario', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='citas', to=settings.AUTH_USER_MODEL)),
                ('solicitud', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='citas', to='solicitudes.solicitud')),
                ('vecino', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='vecinos.vecino')),
            ],
            options={
                'ordering': ['inicio', 'pk'],
            },
        ),
        migrations.CreateModel(
            name='CambioCita',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('anterior', models.CharField(choices=[('programada', 'Programada'), ('atendida', 'Atendida'), ('cancelada', 'Cancelada')], max_length=12)),
                ('nuevo', models.CharField(choices=[('programada', 'Programada'), ('atendida', 'Atendida'), ('cancelada', 'Cancelada')], max_length=12)),
                ('motivo', models.TextField(max_length=1000)),
                ('fecha', models.DateTimeField(auto_now_add=True)),
                ('actor', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ('cita', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='cambios', to='agenda.cita')),
            ],
            options={
                'ordering': ['fecha', 'pk'],
            },
        ),
        migrations.AddConstraint(
            model_name='cita',
            constraint=models.CheckConstraint(condition=models.Q(('fin__gt', models.F('inicio'))), name='cita_fin_posterior'),
        ),
        migrations.AddConstraint(
            model_name='cita',
            constraint=django.contrib.postgres.constraints.ExclusionConstraint(condition=models.Q(('estado', 'programada')), expressions=[('funcionario', '='), (models.Func(models.F('inicio'), models.F('fin'), models.Value('[)'), function='TSTZRANGE', output_field=django.contrib.postgres.fields.ranges.DateTimeRangeField()), '&&')], name='cita_funcionario_sin_superposicion'),
        ),
    ]

````


## apps/agenda/migrations/__init__.py

````

````


## apps/agenda/models.py

````
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateTimeRangeField, RangeOperators
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q


class Cita(models.Model):
    class Estado(models.TextChoices):
        PROGRAMADA = 'programada', 'Programada'
        ATENDIDA = 'atendida', 'Atendida'
        CANCELADA = 'cancelada', 'Cancelada'

    delegacion = models.ForeignKey('delegaciones.Delegacion', on_delete=models.PROTECT)
    vecino = models.ForeignKey('vecinos.Vecino', on_delete=models.PROTECT)
    funcionario = models.ForeignKey('cuentas.Usuario', on_delete=models.PROTECT, related_name='citas')
    solicitud = models.ForeignKey('solicitudes.Solicitud', on_delete=models.PROTECT, null=True, blank=True, related_name='citas')
    inicio = models.DateTimeField()
    fin = models.DateTimeField()
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PROGRAMADA)
    motivo = models.CharField(max_length=300)
    creador = models.ForeignKey('cuentas.Usuario', on_delete=models.PROTECT, related_name='citas_creadas')
    creada_en = models.DateTimeField(auto_now_add=True)
    actualizada_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['inicio', 'pk']
        constraints = [
            models.CheckConstraint(condition=Q(fin__gt=F('inicio')), name='cita_fin_posterior'),
            ExclusionConstraint(
                name='cita_funcionario_sin_superposicion',
                expressions=[
                    ('funcionario', RangeOperators.EQUAL),
                    (models.Func(F('inicio'), F('fin'), models.Value('[)'),
                                 function='TSTZRANGE', output_field=DateTimeRangeField()), RangeOperators.OVERLAPS),
                ],
                condition=Q(estado='programada'),
            ),
        ]

    def clean(self):
        super().clean()
        if self.inicio and self.fin and self.fin <= self.inicio:
            raise ValidationError({'fin': 'El fin debe ser posterior al inicio.'})
        if self.vecino_id and self.vecino.delegacion_id != self.delegacion_id:
            raise ValidationError({'vecino': 'El vecino debe pertenecer a esta delegación.'})
        if self.funcionario_id:
            funcionario = self.funcionario
            if (funcionario.delegacion_id != self.delegacion_id or not funcionario.is_active
                    or funcionario.rol != 'funcionario'):
                raise ValidationError({'funcionario': 'Seleccione un funcionario activo de esta delegación.'})
        if self.solicitud_id and (self.solicitud.delegacion_id != self.delegacion_id
                                 or self.solicitud.vecino_id != self.vecino_id):
            raise ValidationError({'solicitud': 'La solicitud debe corresponder al vecino y la delegación.'})


class CambioCita(models.Model):
    cita = models.ForeignKey(Cita, on_delete=models.PROTECT, related_name='cambios')
    actor = models.ForeignKey('cuentas.Usuario', on_delete=models.PROTECT)
    anterior = models.CharField(max_length=12, choices=Cita.Estado.choices)
    nuevo = models.CharField(max_length=12, choices=Cita.Estado.choices)
    motivo = models.TextField(max_length=1000)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['fecha', 'pk']

````


## apps/agenda/services.py

````
from datetime import timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.cuentas.models import Usuario
from apps.solicitudes.models import Solicitud
from apps.solicitudes.services import auditar, verificar
from .models import Cita, CambioCita


@transaction.atomic
def reservar(usuario, vecino, funcionario, inicio, duracion, motivo, solicitud=None):
    verificar(usuario, vecino.delegacion)
    if timezone.is_naive(inicio):
        raise ValidationError('La fecha debe incluir una zona horaria válida.')
    if inicio <= timezone.now():
        raise ValidationError({'inicio': 'Seleccione una fecha y hora futuras.'})
    if duracion not in (15, 30, 45, 60):
        raise ValidationError({'duracion': 'Seleccione una duración de 15, 30, 45 o 60 minutos.'})
    # Serializes reservations for the same employee; the exclusion constraint
    # also protects against writers that do not use this service.
    funcionario = Usuario.objects.select_for_update().get(pk=funcionario.pk)
    if solicitud is not None:
        solicitud = Solicitud.objects.select_for_update().get(pk=solicitud.pk)
    if solicitud is not None and solicitud.estado == 'cerrada':
        raise ValidationError({'solicitud': 'No se puede reservar atención para una solicitud cerrada.'})
    cita = Cita(delegacion=vecino.delegacion, vecino=vecino, funcionario=funcionario,
                solicitud=solicitud, inicio=inicio, fin=inicio + timedelta(minutes=duracion),
                motivo=motivo.strip(), creador=usuario)
    # The conflict is handled explicitly to return a user-facing message.
    cita.full_clean(validate_constraints=False)
    if Cita.objects.filter(funcionario=funcionario, estado=Cita.Estado.PROGRAMADA,
                           inicio__lt=cita.fin, fin__gt=cita.inicio).exists():
        raise ValidationError('El funcionario ya tiene una atención en ese horario. Elija otro horario o funcionario.')
    try:
        with transaction.atomic():
            cita.save()
    except IntegrityError as error:
        if getattr(error.__cause__, 'sqlstate', None) == '23P01':
            raise ValidationError('Ese horario acaba de ser reservado. Elija otro horario o funcionario.') from error
        raise
    auditar(usuario, 'cita.reservada', cita)
    return cita


@transaction.atomic
def cambiar_estado(usuario, pk, esperado, nuevo, motivo):
    cita = Cita.objects.select_for_update().get(pk=pk)
    verificar(usuario, cita.delegacion)
    if cita.estado != esperado or cita.estado != Cita.Estado.PROGRAMADA:
        raise ValidationError('La cita cambió o ya finalizó. Recargue la página.')
    if nuevo not in (Cita.Estado.CANCELADA, Cita.Estado.ATENDIDA):
        raise ValidationError('El cambio de estado no está permitido.')
    if nuevo == Cita.Estado.ATENDIDA:
        if usuario.pk != cita.funcionario_id and not usuario.supervisa:
            raise PermissionDenied
        if cita.inicio > timezone.now():
            raise ValidationError('La atención no puede completarse antes de su horario de inicio.')
    motivo = motivo.strip()
    if not motivo or len(motivo) > 1000:
        raise ValidationError('Indique un motivo de entre 1 y 1000 caracteres.')
    anterior = cita.estado
    cita.estado = nuevo
    cita.save(update_fields=['estado', 'actualizada_en'])
    CambioCita.objects.create(cita=cita, actor=usuario, anterior=anterior, nuevo=nuevo, motivo=motivo)
    auditar(usuario, f'cita.{nuevo}', cita)
    return cita

````


## apps/agenda/tests.py

````
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

````


## apps/agenda/views.py

````
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import AgendaFiltroForm, CitaForm, CambioCitaForm
from .models import Cita
from .services import reservar, cambiar_estado


@login_required
def agenda(request):
    qs = request.user.scope(Cita.objects.select_related('vecino', 'funcionario', 'delegacion'))
    form = AgendaFiltroForm(request.GET)
    if form.is_valid():
        if form.cleaned_data['fecha']:
            qs = qs.filter(inicio__date=form.cleaned_data['fecha'])
        if form.cleaned_data['estado']:
            qs = qs.filter(estado=form.cleaned_data['estado'])
    else:
        qs = qs.none()
    query = request.GET.copy()
    query.pop('page', None)
    return render(request, 'agenda.html', {'filtros': form,
        'pagina': Paginator(qs, 20).get_page(request.GET.get('page')),
        'filtros_query': query.urlencode()})


@login_required
def cita_crear(request):
    form = CitaForm(request.POST if request.method == 'POST' else None, usuario=request.user)
    if request.method == 'POST' and form.is_valid():
        try:
            cita = reservar(request.user, **form.cleaned_data)
        except ValidationError as error:
            form.add_error(None, ' '.join(error.messages))
        else:
            messages.success(request, 'Atención reservada y registrada en auditoría.')
            return redirect('cita_detalle', pk=cita.pk)
    return render(request, 'form.html', {'form': form, 'titulo': 'Reservar atención'})


def detalle_response(request, cita, form=None, status=200):
    if form is None and cita.estado == Cita.Estado.PROGRAMADA:
        form = CambioCitaForm(usuario=request.user, cita=cita)
    return render(request, 'cita_detalle.html', {'cita': cita, 'form': form,
        'cambios': cita.cambios.select_related('actor')}, status=status)


@login_required
def cita_detalle(request, pk):
    cita = get_object_or_404(request.user.scope(Cita.objects.select_related('vecino', 'funcionario', 'delegacion', 'solicitud')), pk=pk)
    return detalle_response(request, cita)


@login_required
@require_POST
def cita_estado(request, pk):
    cita = get_object_or_404(request.user.scope(Cita.objects.all()), pk=pk)
    form = CambioCitaForm(request.POST, usuario=request.user, cita=cita)
    if form.is_valid():
        try:
            cambiar_estado(request.user, pk, **form.cleaned_data)
        except ValidationError as error:
            form.add_error(None, ' '.join(error.messages))
            return detalle_response(request, cita, form, status=409)
        messages.success(request, 'Estado de la atención actualizado.')
        return redirect('cita_detalle', pk=pk)
    return detalle_response(request, cita, form, status=400)

````


## apps/auditoria/__init__.py

````

````


## apps/auditoria/migrations/0001_initial.py

````
# Generated by Django 5.2.18 on 2026-10-07 21:00

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Evento',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('accion', models.CharField(max_length=80)),
                ('entidad', models.CharField(max_length=80)),
                ('objeto_id', models.CharField(max_length=80)),
                ('fecha', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-fecha', '-pk'],
            },
        ),
    ]

````


## apps/auditoria/migrations/0002_initial.py

````
# Generated by Django 5.2.18 on 2026-10-07 21:00

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auditoria', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='evento',
            name='actor',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL),
        ),
    ]

````


## apps/auditoria/migrations/__init__.py

````

````


## apps/auditoria/models.py

````
from django.db import models

class Evento(models.Model):
    actor = models.ForeignKey('cuentas.Usuario', on_delete=models.PROTECT, null=True)
    accion = models.CharField(max_length=80)
    entidad = models.CharField(max_length=80)
    objeto_id = models.CharField(max_length=80)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha', '-pk']

````


## apps/cuentas/__init__.py

````

````


## apps/cuentas/admin.py

````
from django.contrib import admin
from django.contrib.admin import AdminSite
from django.contrib.auth.admin import UserAdmin
from django.core.exceptions import PermissionDenied
from django.contrib.admin.utils import unquote
from django.db import transaction
from apps.delegaciones.models import Delegacion
from apps.auditoria.models import Evento
from apps.solicitudes.services import auditar
from .models import Usuario

class MunicipalAdminSite(AdminSite):
    site_header = 'Administración municipal'
    site_title = 'Delegaciones Municipales'
    index_title = 'Usuarios y delegaciones'

    def has_permission(self, request):
        return request.user.is_authenticated and request.user.is_active and request.user.administra and request.user.is_staff

municipal_site = MunicipalAdminSite(name='admin')

class ConservacionAdmin(admin.ModelAdmin):
    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        auditar(request.user, 'administracion.editado' if change else 'administracion.creado', obj)

class UsuarioAdmin(ConservacionAdmin, UserAdmin):
    fieldsets = UserAdmin.fieldsets + (('Ámbito municipal', {'fields': ('rol', 'delegacion')}),)
    add_fieldsets = UserAdmin.add_fieldsets + (('Ámbito municipal', {'fields': ('rol', 'delegacion')}),)
    list_display = ['username', 'rol', 'delegacion', 'is_active']
    list_filter = ['rol', 'delegacion', 'is_active']
    actions = None

    @transaction.atomic
    def user_change_password(self, request, id, form_url=''):
        response = super().user_change_password(request, id, form_url)
        if request.method == 'POST' and response.status_code == 302:
            usuario = self.get_object(request, unquote(id))
            auditar(request.user, 'usuario.password_cambiada', usuario)
        return response

    def save_model(self, request, obj, form, change):
        if obj.pk == request.user.pk and (not obj.is_active or not obj.administra):
            raise PermissionDenied('No se puede desactivar o degradar su propia cuenta.')
        obj.is_staff = obj.administra
        obj.is_superuser = obj.administra
        super().save_model(request, obj, form, change)

class EventoAdmin(admin.ModelAdmin):
    list_display = ['fecha', 'actor', 'accion', 'entidad', 'objeto_id']
    readonly_fields = ['fecha', 'actor', 'accion', 'entidad', 'objeto_id']
    actions = None
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False

municipal_site.register(Usuario, UsuarioAdmin)
municipal_site.register(Delegacion, ConservacionAdmin)
municipal_site.register(Evento, EventoAdmin)

````


## apps/cuentas/apps.py

````
from django.apps import AppConfig

class CuentasConfig(AppConfig):
    name = 'apps.cuentas'

    def ready(self):
        from . import signals  # noqa: F401

````


## apps/cuentas/migrations/0001_initial.py

````
# Generated by Django 5.2.18 on 2026-10-07 21:00

import django.contrib.auth.models
import django.contrib.auth.validators
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('delegaciones', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Usuario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.CharField(error_messages={'unique': 'A user with that username already exists.'}, help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.', max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name='username')),
                ('first_name', models.CharField(blank=True, max_length=150, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('email', models.EmailField(blank=True, max_length=254, verbose_name='email address')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('rol', models.CharField(choices=[('funcionario', 'Funcionario'), ('delegado', 'Delegado'), ('administrador', 'Administrador')], default='funcionario', max_length=20)),
                ('delegacion', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='delegaciones.delegacion')),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'verbose_name': 'user',
                'verbose_name_plural': 'users',
                'abstract': False,
            },
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
    ]

````


## apps/cuentas/migrations/__init__.py

````

````


## apps/cuentas/models.py

````
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models

class Usuario(AbstractUser):
    class Rol(models.TextChoices):
        FUNCIONARIO = 'funcionario', 'Funcionario'
        DELEGADO = 'delegado', 'Delegado'
        ADMINISTRADOR = 'administrador', 'Administrador'

    rol = models.CharField(max_length=20, choices=Rol.choices, default=Rol.FUNCIONARIO)
    delegacion = models.ForeignKey('delegaciones.Delegacion', on_delete=models.PROTECT, null=True, blank=True)

    def clean(self):
        super().clean()
        if self.rol != self.Rol.ADMINISTRADOR and not self.delegacion_id:
            raise ValidationError({'delegacion': 'Este rol requiere una delegación.'})
        if self.pk and self.asignadas.exclude(estado='cerrada').exclude(delegacion_id=self.delegacion_id).exists():
            raise ValidationError({'delegacion': 'Debe finalizar las solicitudes asignadas antes de cambiar de delegación.'})
        if self.pk and self.citas.filter(estado='programada').exclude(delegacion_id=self.delegacion_id).exists():
            raise ValidationError({'delegacion': 'Debe finalizar o cancelar las citas antes de cambiar de delegación.'})
        if self.pk and self.rol != self.Rol.FUNCIONARIO and self.citas.filter(estado='programada').exists():
            raise ValidationError({'rol': 'Debe finalizar o cancelar las citas antes de cambiar de rol.'})
        if self.pk and not self.is_active and self.citas.filter(estado='programada').exists():
            raise ValidationError({'is_active': 'Debe finalizar o cancelar las citas antes de desactivar al funcionario.'})

    @property
    def administra(self):
        return self.rol == self.Rol.ADMINISTRADOR

    @property
    def supervisa(self):
        return self.rol in (self.Rol.DELEGADO, self.Rol.ADMINISTRADOR)

    def tiene_acceso(self, delegacion):
        return self.is_active and delegacion.activa and (self.administra or self.delegacion_id == delegacion.pk)

    def scope(self, queryset):
        queryset = queryset.filter(delegacion__activa=True)
        if self.administra:
            return queryset
        if not self.delegacion_id:
            return queryset.none()
        return queryset.filter(delegacion_id=self.delegacion_id)

````


## apps/cuentas/signals.py

````
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from apps.auditoria.models import Evento

@receiver(user_logged_in)
def login(sender, request, user, **kwargs):
    Evento.objects.create(actor=user, accion='acceso.exitoso', entidad='cuentas.Usuario', objeto_id=str(user.pk))

@receiver(user_logged_out)
def logout(sender, request, user, **kwargs):
    if user:
        Evento.objects.create(actor=user, accion='acceso.salida', entidad='cuentas.Usuario', objeto_id=str(user.pk))

@receiver(user_login_failed)
def failed(sender, credentials, request, **kwargs):
    # Do not persist supplied usernames or passwords.
    Evento.objects.create(accion='acceso.fallido', entidad='cuentas.Usuario', objeto_id='')

````


## apps/cuentas/test_proxy.py

````
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

````


## apps/cuentas/tests.py

````
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

````


## apps/delegaciones/__init__.py

````

````


## apps/delegaciones/migrations/0001_initial.py

````
# Generated by Django 5.2.18 on 2026-10-07 21:00

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Delegacion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=120, unique=True)),
                ('direccion', models.CharField(max_length=200, verbose_name='dirección')),
                ('activa', models.BooleanField(default=True)),
            ],
        ),
    ]

````


## apps/delegaciones/migrations/__init__.py

````

````


## apps/delegaciones/models.py

````
from django.db import models

class Delegacion(models.Model):
    nombre = models.CharField(max_length=120, unique=True)
    direccion = models.CharField('dirección', max_length=200)
    activa = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre

````


## apps/reportes/__init__.py

````

````


## apps/reportes/forms.py

````
from django import forms

from apps.delegaciones.models import Delegacion
from apps.solicitudes.models import Solicitud


class ReporteForm(forms.Form):
    desde = forms.DateField(label='Desde (fecha de ingreso)', required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    hasta = forms.DateField(label='Hasta (inclusive)', required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    estado = forms.ChoiceField(required=False, choices=[('', 'Todos los estados')] + Solicitud.Estado.choices)
    delegacion = forms.ModelChoiceField(queryset=Delegacion.objects.none(), required=False, label='Delegación')

    def __init__(self, *args, usuario, **kwargs):
        super().__init__(*args, **kwargs)
        delegaciones = Delegacion.objects.filter(activa=True)
        if not usuario.administra:
            delegaciones = delegaciones.filter(pk=usuario.delegacion_id)
        self.fields['delegacion'].queryset = delegaciones.order_by('nombre')
        self.fields['delegacion'].empty_label = 'Todas las autorizadas'

    def clean(self):
        data = super().clean()
        desde, hasta = data.get('desde'), data.get('hasta')
        if desde and hasta and hasta < desde:
            raise forms.ValidationError('La fecha final debe ser igual o posterior a la inicial.')
        return data

````


## apps/reportes/tests.py

````
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

````


## apps/reportes/views.py

````
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import render

from apps.solicitudes.models import Solicitud
from .forms import ReporteForm


@login_required
def reportes(request):
    if not request.user.supervisa:
        raise PermissionDenied
    form = ReporteForm(request.GET, usuario=request.user)
    qs = request.user.scope(Solicitud.objects.select_related('vecino', 'delegacion', 'responsable'))
    if form.is_valid():
        data = form.cleaned_data
        if data['desde']:
            qs = qs.filter(creada_en__date__gte=data['desde'])
        if data['hasta']:
            qs = qs.filter(creada_en__date__lte=data['hasta'])
        if data['estado']:
            qs = qs.filter(estado=data['estado'])
        if data['delegacion']:
            qs = qs.filter(delegacion=data['delegacion'])
    else:
        # Invalid or unauthorized filters never fall back to a wider report.
        qs = qs.none()
    counts = {row['estado']: row['total'] for row in qs.order_by().values('estado').annotate(total=Count('pk'))}
    por_estado = [{'nombre': label, 'total': counts.get(value, 0)} for value, label in Solicitud.Estado.choices]
    por_delegacion = qs.order_by().values('delegacion__nombre').annotate(total=Count('pk')).order_by('delegacion__nombre')
    query = request.GET.copy()
    query.pop('page', None)
    return render(request, 'reportes.html', {'filtros': form, 'total': qs.count(), 'por_estado': por_estado,
        'por_delegacion': por_delegacion, 'pagina': Paginator(qs, 20).get_page(request.GET.get('page')),
        'filtros_query': query.urlencode()})

````


## apps/solicitudes/__init__.py

````

````


## apps/solicitudes/forms.py

````
from django import forms
from apps.cuentas.models import Usuario
from apps.vecinos.models import Vecino
from .models import Solicitud

class SolicitudForm(forms.Form):
    vecino = forms.ModelChoiceField(queryset=Vecino.objects.none())
    tipo = forms.ChoiceField(choices=Solicitud.Tipo.choices)
    descripcion = forms.CharField(label='Descripción', max_length=3000, widget=forms.Textarea)

    def __init__(self, *args, usuario, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['vecino'].queryset = usuario.scope(Vecino.objects.all())

class TransicionForm(forms.Form):
    esperado = forms.ChoiceField(choices=Solicitud.Estado.choices, widget=forms.HiddenInput)
    nuevo = forms.ChoiceField(choices=Solicitud.Estado.choices, widget=forms.HiddenInput)
    responsable = forms.ModelChoiceField(queryset=Usuario.objects.none(), required=False)
    motivo = forms.CharField(label='Observación / solución', max_length=2000, strip=True, widget=forms.Textarea)

    def __init__(self, *args, solicitud, nuevo, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['esperado'].initial = solicitud.estado
        self.fields['nuevo'].initial = nuevo
        self.fields['responsable'].queryset = Usuario.objects.filter(is_active=True, delegacion=solicitud.delegacion)
        if nuevo != Solicitud.Estado.ASIGNADA:
            self.fields['responsable'].widget = forms.HiddenInput()
        else:
            self.fields['responsable'].required = True

class ObservacionForm(forms.Form):
    texto = forms.CharField(label='Observación', max_length=2000, strip=True, widget=forms.Textarea)

````


## apps/solicitudes/migrations/0001_initial.py

````
# Generated by Django 5.2.18 on 2026-10-07 21:00

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('delegaciones', '0001_initial'),
        ('vecinos', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Solicitud',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('folio', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('tipo', models.CharField(choices=[('certificado', 'Certificado'), ('permiso', 'Permiso'), ('reclamo', 'Reclamo'), ('otro', 'Otro')], max_length=20)),
                ('descripcion', models.TextField(max_length=3000, verbose_name='descripción')),
                ('estado', models.CharField(choices=[('ingresada', 'Ingresada'), ('asignada', 'Asignada'), ('atencion', 'En atención'), ('resuelta', 'Resuelta'), ('cerrada', 'Cerrada')], default='ingresada', max_length=20)),
                ('creada_en', models.DateTimeField(auto_now_add=True)),
                ('actualizada_en', models.DateTimeField(auto_now=True)),
                ('creador', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='creadas', to=settings.AUTH_USER_MODEL)),
                ('delegacion', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='delegaciones.delegacion')),
                ('responsable', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='asignadas', to=settings.AUTH_USER_MODEL)),
                ('vecino', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='vecinos.vecino')),
            ],
            options={
                'ordering': ['-creada_en'],
            },
        ),
        migrations.CreateModel(
            name='Observacion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('texto', models.TextField(max_length=2000)),
                ('fecha', models.DateTimeField(auto_now_add=True)),
                ('autor', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ('solicitud', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='observaciones', to='solicitudes.solicitud')),
            ],
            options={
                'ordering': ['fecha', 'pk'],
            },
        ),
        migrations.CreateModel(
            name='CambioEstado',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('anterior', models.CharField(choices=[('ingresada', 'Ingresada'), ('asignada', 'Asignada'), ('atencion', 'En atención'), ('resuelta', 'Resuelta'), ('cerrada', 'Cerrada')], max_length=20)),
                ('nuevo', models.CharField(choices=[('ingresada', 'Ingresada'), ('asignada', 'Asignada'), ('atencion', 'En atención'), ('resuelta', 'Resuelta'), ('cerrada', 'Cerrada')], max_length=20)),
                ('motivo', models.TextField(max_length=2000)),
                ('fecha', models.DateTimeField(auto_now_add=True)),
                ('actor', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ('solicitud', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='cambios', to='solicitudes.solicitud')),
            ],
            options={
                'ordering': ['fecha', 'pk'],
            },
        ),
    ]

````


## apps/solicitudes/migrations/__init__.py

````

````


## apps/solicitudes/models.py

````
import uuid
from django.core.exceptions import ValidationError
from django.db import models

class Solicitud(models.Model):
    class Estado(models.TextChoices):
        INGRESADA = 'ingresada', 'Ingresada'
        ASIGNADA = 'asignada', 'Asignada'
        ATENCION = 'atencion', 'En atención'
        RESUELTA = 'resuelta', 'Resuelta'
        CERRADA = 'cerrada', 'Cerrada'
    class Tipo(models.TextChoices):
        CERTIFICADO = 'certificado', 'Certificado'
        PERMISO = 'permiso', 'Permiso'
        RECLAMO = 'reclamo', 'Reclamo'
        OTRO = 'otro', 'Otro'

    folio = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    delegacion = models.ForeignKey('delegaciones.Delegacion', on_delete=models.PROTECT)
    vecino = models.ForeignKey('vecinos.Vecino', on_delete=models.PROTECT)
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    descripcion = models.TextField('descripción', max_length=3000)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.INGRESADA)
    creador = models.ForeignKey('cuentas.Usuario', on_delete=models.PROTECT, related_name='creadas')
    responsable = models.ForeignKey('cuentas.Usuario', on_delete=models.PROTECT, null=True, blank=True, related_name='asignadas')
    creada_en = models.DateTimeField(auto_now_add=True)
    actualizada_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-creada_en']

    def clean(self):
        super().clean()
        if self.vecino_id and self.vecino.delegacion_id != self.delegacion_id:
            raise ValidationError('El vecino debe pertenecer a la delegación de la solicitud.')
        if self.responsable_id and self.responsable.delegacion_id != self.delegacion_id:
            raise ValidationError('El responsable debe pertenecer a la misma delegación.')

class Observacion(models.Model):
    solicitud = models.ForeignKey(Solicitud, on_delete=models.PROTECT, related_name='observaciones')
    autor = models.ForeignKey('cuentas.Usuario', on_delete=models.PROTECT)
    texto = models.TextField(max_length=2000)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['fecha', 'pk']

class CambioEstado(models.Model):
    solicitud = models.ForeignKey(Solicitud, on_delete=models.PROTECT, related_name='cambios')
    actor = models.ForeignKey('cuentas.Usuario', on_delete=models.PROTECT)
    anterior = models.CharField(max_length=20, choices=Solicitud.Estado.choices)
    nuevo = models.CharField(max_length=20, choices=Solicitud.Estado.choices)
    motivo = models.TextField(max_length=2000)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['fecha', 'pk']

````


## apps/solicitudes/services.py

````
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from apps.auditoria.models import Evento
from apps.cuentas.models import Usuario
from .models import Solicitud, CambioEstado, Observacion

def auditar(usuario, accion, objeto):
    Evento.objects.create(actor=usuario, accion=accion, entidad=objeto._meta.label, objeto_id=str(objeto.pk))

def verificar(usuario, delegacion):
    if not usuario.tiene_acceso(delegacion):
        raise PermissionDenied

@transaction.atomic
def crear_solicitud(usuario, vecino, tipo, descripcion):
    verificar(usuario, vecino.delegacion)
    solicitud = Solicitud(delegacion=vecino.delegacion, vecino=vecino, tipo=tipo,
                          descripcion=descripcion, creador=usuario)
    solicitud.full_clean()
    solicitud.save()
    auditar(usuario, 'solicitud.creada', solicitud)
    return solicitud

@transaction.atomic
def transicionar(usuario, pk, esperado, nuevo, motivo, responsable_id=None):
    solicitud = Solicitud.objects.select_for_update().get(pk=pk)
    verificar(usuario, solicitud.delegacion)
    if solicitud.estado != esperado:
        raise ValidationError('La solicitud cambió. Recargue la página antes de continuar.')
    destinos = {
        Solicitud.Estado.INGRESADA: Solicitud.Estado.ASIGNADA,
        Solicitud.Estado.ASIGNADA: Solicitud.Estado.ATENCION,
        Solicitud.Estado.ATENCION: Solicitud.Estado.RESUELTA,
        Solicitud.Estado.RESUELTA: Solicitud.Estado.CERRADA,
    }
    if destinos.get(solicitud.estado) != nuevo:
        raise ValidationError('La transición solicitada no está permitida.')
    motivo = motivo.strip()
    if not motivo or len(motivo) > 2000:
        raise ValidationError('Indique una observación de entre 1 y 2000 caracteres.')
    if nuevo in (Solicitud.Estado.ASIGNADA, Solicitud.Estado.CERRADA):
        if not usuario.supervisa:
            raise PermissionDenied
    elif not usuario.supervisa and solicitud.responsable_id != usuario.pk:
        raise PermissionDenied
    if nuevo == Solicitud.Estado.ASIGNADA:
        responsable = Usuario.objects.filter(pk=responsable_id, is_active=True,
                                              delegacion=solicitud.delegacion).first()
        if not responsable:
            raise ValidationError('Seleccione un responsable activo de esta delegación.')
        solicitud.responsable = responsable
    anterior = solicitud.estado
    solicitud.estado = nuevo
    solicitud.full_clean()
    solicitud.save(update_fields=['estado', 'responsable', 'actualizada_en'])
    CambioEstado.objects.create(solicitud=solicitud, actor=usuario, anterior=anterior, nuevo=nuevo, motivo=motivo)
    Observacion.objects.create(solicitud=solicitud, autor=usuario, texto=motivo)
    auditar(usuario, f'solicitud.{nuevo}', solicitud)
    return solicitud

@transaction.atomic
def agregar_observacion(usuario, pk, texto):
    solicitud = Solicitud.objects.select_for_update().get(pk=pk)
    verificar(usuario, solicitud.delegacion)
    if solicitud.estado == Solicitud.Estado.CERRADA:
        raise ValidationError('No se pueden agregar observaciones a una solicitud cerrada.')
    texto = texto.strip()
    if not texto or len(texto) > 2000:
        raise ValidationError('Indique una observación de entre 1 y 2000 caracteres.')
    observacion = Observacion.objects.create(solicitud=solicitud, autor=usuario, texto=texto)
    auditar(usuario, 'observacion.creada', observacion)

````


## apps/solicitudes/tests.py

````
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

````


## apps/vecinos/__init__.py

````

````


## apps/vecinos/forms.py

````
from django import forms
from apps.delegaciones.models import Delegacion
from .models import Vecino, normalizar_rut

class VecinoForm(forms.ModelForm):
    class Meta:
        model = Vecino
        fields = ['delegacion', 'rut', 'nombre', 'email', 'telefono', 'direccion']

    def __init__(self, *args, usuario, **kwargs):
        super().__init__(*args, **kwargs)
        qs = Delegacion.objects.filter(activa=True)
        if not usuario.administra:
            qs = qs.filter(pk=usuario.delegacion_id)
        self.fields['delegacion'].queryset = qs
        if not usuario.administra:
            self.fields['delegacion'].initial = usuario.delegacion_id
            self.fields['delegacion'].disabled = True
        if self.instance.pk:
            self.fields['delegacion'].initial = self.instance.delegacion_id
            self.fields['delegacion'].disabled = True

    def clean_rut(self):
        return normalizar_rut(self.cleaned_data['rut'])

````


## apps/vecinos/migrations/0001_initial.py

````
# Generated by Django 5.2.18 on 2026-10-07 21:00

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('delegaciones', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Vecino',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rut', models.CharField(max_length=12, verbose_name='RUT')),
                ('nombre', models.CharField(max_length=160)),
                ('email', models.EmailField(blank=True, max_length=254, verbose_name='correo electrónico')),
                ('telefono', models.CharField(blank=True, max_length=25, verbose_name='teléfono')),
                ('direccion', models.CharField(max_length=200, verbose_name='dirección')),
                ('delegacion', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='delegaciones.delegacion')),
            ],
            options={
                'ordering': ['nombre'],
                'constraints': [models.UniqueConstraint(fields=('delegacion', 'rut'), name='rut_por_delegacion')],
            },
        ),
    ]

````


## apps/vecinos/migrations/__init__.py

````

````


## apps/vecinos/models.py

````
import re
from django.core.exceptions import ValidationError
from django.db import models

def normalizar_rut(value):
    rut = value.replace('.', '').replace('-', '').strip().upper()
    if not re.fullmatch(r'[0-9]{1,8}[0-9K]', rut):
        raise ValidationError('Ingrese un RUT chileno válido, con dígito verificador.')
    cuerpo, dv = rut[:-1], rut[-1]
    if int(cuerpo) == 0:
        raise ValidationError('El número de RUT debe ser positivo.')
    total = sum(int(d) * (2 + i % 6) for i, d in enumerate(reversed(cuerpo)))
    resultado = 11 - total % 11
    esperado = '0' if resultado == 11 else 'K' if resultado == 10 else str(resultado)
    if dv != esperado:
        raise ValidationError('El dígito verificador del RUT no es válido.')
    return f'{int(cuerpo)}-{dv}'

class Vecino(models.Model):
    delegacion = models.ForeignKey('delegaciones.Delegacion', on_delete=models.PROTECT)
    rut = models.CharField('RUT', max_length=12)
    nombre = models.CharField(max_length=160)
    email = models.EmailField('correo electrónico', blank=True)
    telefono = models.CharField('teléfono', max_length=25, blank=True)
    direccion = models.CharField('dirección', max_length=200)

    class Meta:
        ordering = ['nombre']
        constraints = [models.UniqueConstraint(fields=['delegacion', 'rut'], name='rut_por_delegacion')]

    def clean(self):
        super().clean()
        self.rut = normalizar_rut(self.rut)
        if not self.email and not self.telefono:
            raise ValidationError('Indique al menos un correo o teléfono de contacto.')

    def __str__(self):
        return f'{self.nombre} · {self.rut}'

````


## compose.ec2.yaml

````
name: delegaciones-ec2

x-app: &app
  image: delegaciones-municipales-ec2:local
  build:
    context: .
    dockerfile: Dockerfile.ec2
  read_only: true
  tmpfs:
    - /tmp
  security_opt:
    - no-new-privileges:true
  volumes:
    - configuracion:/app/.local

services:
  init:
    <<: *app
    command: ["python", "scripts/init_ec2.py"]
    volumes:
      - configuracion:/app/.local
      - administracion:/run/db-admin
    restart: "no"
    networks: [database]

  db:
    image: postgres:17@sha256:2d2b8998d31037bf721cfdf764d76ba74171b4fab3431b7f72c27c56ddbdf9e3
    environment:
      POSTGRES_USER: postgres
      POSTGRES_DB: delegaciones
      POSTGRES_PASSWORD_FILE: /run/db-admin/password.txt
    volumes:
      - datos:/var/lib/postgresql/data
      - administracion:/run/db-admin:ro
    depends_on:
      init:
        condition: service_completed_successfully
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d delegaciones"]
      interval: 3s
      timeout: 3s
      retries: 30
    restart: unless-stopped
    networks: [database]

  provision:
    <<: *app
    command: ["python", "scripts/provision_ec2.py"]
    volumes:
      - configuracion:/app/.local
      - administracion:/run/db-admin:ro
    depends_on:
      db:
        condition: service_healthy
    restart: "no"
    networks: [database]

  web:
    <<: *app
    environment:
      POSTGRES_HOST: db
      POSTGRES_PORT: "5432"
      DJANGO_DEBUG: "false"
      DJANGO_TRUST_PROXY: "true"
      DJANGO_ALLOWED_HOSTS: ${PUBLIC_IP:?Prepare .local/ec2.env},localhost,127.0.0.1
      SEED_DEMO: "true"
    volumes:
      - configuracion:/app/.local
      - estaticos:/app/staticfiles
    depends_on:
      provision:
        condition: service_completed_successfully
    healthcheck:
      test: ["CMD", "python", "scripts/check_ec2.py"]
      interval: 5s
      timeout: 5s
      retries: 30
      start_period: 30s
    restart: unless-stopped
    networks: [application, database]

  proxy:
    image: nginx:1.28-alpine@sha256:a8b39bd9cf0f83869a2162827a0caf6137ddf759d50a171451b335cecc87d236
    entrypoint: ["nginx"]
    command: ["-g", "daemon off;"]
    ports:
      - "${BIND_ADDRESS:-0.0.0.0}:${HTTP_PORT:-80}:80"
      - "${BIND_ADDRESS:-0.0.0.0}:${HTTPS_PORT:-443}:443"
    volumes:
      - ./.local/ec2/nginx:/etc/nginx/conf.d:ro
      - certificados:/etc/letsencrypt:ro
      - acme:/var/www/acme:ro
      - estaticos:/var/www/static:ro
    read_only: true
    tmpfs:
      - /var/cache/nginx
      - /var/run
      - /tmp
    security_opt:
      - no-new-privileges:true
    restart: unless-stopped
    networks: [application, edge]

  certbot:
    image: certbot/certbot:v5.8.0@sha256:f70ad0adbb7e117f0fe42a63c553f28ea451edabc0148757b6efcd9735acaa20
    volumes:
      - certificados:/etc/letsencrypt
      - acme:/var/www/acme
      - registros_acme:/var/log/letsencrypt
    profiles: [tools]
    networks: [edge]

volumes:
  configuracion:
  administracion:
  datos:
  estaticos:
  certificados:
  acme:
  registros_acme:

networks:
  edge:
  application:
    internal: true
  database:
    internal: true

````


## compose.https.yaml

````
# Local TLS demonstration; not an internet deployment.
services:
  web:
    environment:
      DJANGO_DEBUG: "false"
      LOCAL_HTTPS: "true"
    command: ["sh", "scripts/start_https.sh"]

````


## compose.yaml

````
name: delegaciones-municipales

x-app: &app
  image: delegaciones-municipales-demo:local
  build: .
  read_only: true
  tmpfs:
    - /tmp
  security_opt:
    - no-new-privileges:true
  volumes:
    - configuracion:/app/.local

services:
  init:
    <<: *app
    command: ["python", "scripts/init_container.py"]
    restart: "no"

  db:
    image: postgres:17@sha256:2d2b8998d31037bf721cfdf764d76ba74171b4fab3431b7f72c27c56ddbdf9e3
    environment:
      POSTGRES_USER: delegaciones
      POSTGRES_DB: delegaciones
      POSTGRES_PASSWORD_FILE: /run/app-config/postgres-password.txt
    volumes:
      - datos:/var/lib/postgresql/data
      - configuracion:/run/app-config:ro
    depends_on:
      init:
        condition: service_completed_successfully
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U delegaciones -d delegaciones"]
      interval: 3s
      timeout: 3s
      retries: 30
    restart: unless-stopped

  web:
    <<: *app
    environment:
      POSTGRES_HOST: db
      POSTGRES_PORT: "5432"
      DJANGO_ALLOWED_HOSTS: localhost,127.0.0.1
    ports:
      - "127.0.0.1:${APP_PORT:-8000}:8000"
    depends_on:
      init:
        condition: service_completed_successfully
      db:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "python", "scripts/check_ready.py"]
      interval: 5s
      timeout: 5s
      retries: 20
      start_period: 15s
    restart: unless-stopped

volumes:
  configuracion:
  datos:

````


## config/__init__.py

````

````


## config/middleware.py

````
from django.utils.cache import patch_cache_control
from django.conf import settings
from django.contrib.auth import logout
from django.shortcuts import redirect
from time import time


class InactividadMiddleware:
    """Reject expired sessions before private views, renewing on authenticated requests."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            now = time()
            last = request.session.get('ultima_actividad', now)
            if now - last >= settings.SESSION_IDLE_TIMEOUT:
                logout(request)
                return redirect('login')
            request.session['ultima_actividad'] = now
        response = self.get_response(request)
        if request.user.is_authenticated:
            request.session.setdefault('ultima_actividad', time())
        return response


class DatosPrivadosMiddleware:
    """Prevent shared/browser caches from retaining authenticated municipal data."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        patch_cache_control(response, private=True, no_store=True)
        response['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        return response

````


## config/network.py

````
"""Client addressing at the explicitly configured reverse-proxy boundary."""
from ipaddress import ip_address
from django.conf import settings


def client_ip(request):
    address = request.META.get('REMOTE_ADDR')
    if settings.TRUST_PROXY:
        candidate = request.META.get('HTTP_X_REAL_IP', '')
        try:
            return str(ip_address(candidate))
        except ValueError:
            pass
    return address

````


## config/settings.py

````
import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
local = BASE_DIR / '.local' / 'config.json'
LOCAL = json.loads(local.read_text()) if local.exists() else {}

def setting(name, default=None):
    return os.environ.get(name, LOCAL.get(name, default))

SECRET_KEY = setting('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    raise RuntimeError('Configure DJANGO_SECRET_KEY o ejecute scripts/prepare.py.')
DEBUG = setting('DJANGO_DEBUG', 'false').lower() == 'true'
ALLOWED_HOSTS = setting('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
INSTALLED_APPS = [
    'django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes',
    'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles',
    'axes', 'apps.delegaciones', 'apps.cuentas', 'apps.vecinos',
    'apps.solicitudes', 'apps.auditoria', 'apps.agenda', 'apps.reportes',
]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware', 'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware', 'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware', 'django.contrib.messages.middleware.MessageMiddleware',
    'config.middleware.DatosPrivadosMiddleware',
    'config.middleware.InactividadMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware', 'axes.middleware.AxesMiddleware',
]
ROOT_URLCONF = 'config.urls'
TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [BASE_DIR / 'templates'],
              'APP_DIRS': True, 'OPTIONS': {'context_processors': [
                  'django.template.context_processors.request', 'django.contrib.auth.context_processors.auth',
                  'django.contrib.messages.context_processors.messages']}}]
WSGI_APPLICATION = 'config.wsgi.application'
DATABASES = {'default': {'ENGINE': 'django.db.backends.postgresql',
    'NAME': setting('POSTGRES_DB', 'delegaciones'), 'USER': setting('POSTGRES_USER', 'delegaciones'),
    'PASSWORD': setting('POSTGRES_PASSWORD'), 'HOST': setting('POSTGRES_HOST', '127.0.0.1'),
    'PORT': setting('POSTGRES_PORT', '55432')}}
AUTH_USER_MODEL = 'cuentas.Usuario'
AUTHENTICATION_BACKENDS = ['axes.backends.AxesStandaloneBackend', 'django.contrib.auth.backends.ModelBackend']
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 12}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1
AXES_LOCKOUT_PARAMETERS = [['username', 'ip_address']]
AXES_LOCKOUT_TEMPLATE = 'registration/locked.html'
AXES_CLIENT_IP_CALLABLE = 'config.network.client_ip'
LANGUAGE_CODE = 'es-cl'
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_TZ = True
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'inicio'
LOGOUT_REDIRECT_URL = 'login'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 1800
SESSION_IDLE_TIMEOUT = 1800
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG

# Only enable behind the private EC2 network, where Nginx overwrites this header.
TRUST_PROXY = setting('DJANGO_TRUST_PROXY', 'false').lower() == 'true'
if TRUST_PROXY:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

````


## config/urls.py

````
from apps.cuentas.admin import municipal_site
from django.contrib.auth import views as auth_views
from django.urls import path
from . import views
from apps.agenda import views as agenda_views
from apps.reportes import views as reporte_views

urlpatterns = [
    path('admin/', municipal_site.urls),
    path('acceso/', auth_views.LoginView.as_view(), name='login'),
    path('salir/', auth_views.LogoutView.as_view(), name='logout'),
    path('sesion/actividad/', views.actividad, name='actividad'),
    path('', views.inicio, name='inicio'),
    path('vecinos/', views.vecinos, name='vecinos'),
    path('vecinos/nuevo/', views.vecino_editar, name='vecino_crear'),
    path('vecinos/<int:pk>/editar/', views.vecino_editar, name='vecino_editar'),
    path('solicitudes/', views.solicitudes, name='solicitudes'),
    path('solicitudes/nueva/', views.solicitud_crear, name='solicitud_crear'),
    path('solicitudes/<int:pk>/', views.solicitud_detalle, name='solicitud_detalle'),
    path('solicitudes/<int:pk>/estado/', views.solicitud_transicion, name='solicitud_transicion'),
    path('solicitudes/<int:pk>/observacion/', views.solicitud_observacion, name='solicitud_observacion'),
    path('auditoria/', views.auditoria, name='auditoria'),
    path('agenda/', agenda_views.agenda, name='agenda'),
    path('agenda/nueva/', agenda_views.cita_crear, name='cita_crear'),
    path('agenda/<int:pk>/', agenda_views.cita_detalle, name='cita_detalle'),
    path('agenda/<int:pk>/estado/', agenda_views.cita_estado, name='cita_estado'),
    path('reportes/', reporte_views.reportes, name='reportes'),
]

````


## config/views.py

````
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from apps.auditoria.models import Evento
from apps.vecinos.models import Vecino
from apps.vecinos.forms import VecinoForm
from apps.solicitudes.models import Solicitud
from apps.solicitudes.forms import SolicitudForm, TransicionForm, ObservacionForm
from apps.solicitudes.services import crear_solicitud, transicionar, agregar_observacion, auditar, verificar
from django.http import JsonResponse


@login_required
@require_POST
def actividad(request):
    return JsonResponse({'activa': True})

@login_required
def inicio(request):
    qs = request.user.scope(Solicitud.objects.all())
    return render(request, 'inicio.html', {'total': qs.count(), 'pendientes': qs.exclude(estado='cerrada').count(),
                                         'solicitudes': qs.select_related('vecino', 'delegacion')[:5]})

@login_required
def vecinos(request):
    qs = request.user.scope(Vecino.objects.select_related('delegacion'))
    q = request.GET.get('q', '').strip()[:100]
    if q:
        qs = qs.filter(Q(nombre__icontains=q) | Q(rut__icontains=q))
    from django.core.paginator import Paginator
    return render(request, 'vecinos.html', {'pagina': Paginator(qs, 20).get_page(request.GET.get('page')), 'q': q})

@login_required
def vecino_editar(request, pk=None):
    vecino = get_object_or_404(request.user.scope(Vecino.objects.all()), pk=pk) if pk else None
    form = VecinoForm(request.POST if request.method == 'POST' else None, instance=vecino, usuario=request.user)
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                objeto = form.save(commit=False)
                verificar(request.user, objeto.delegacion)
                objeto.save()
                auditar(request.user, 'vecino.editado' if pk else 'vecino.creado', objeto)
        except IntegrityError as error:
            constraint = getattr(getattr(error.__cause__, 'diag', None), 'constraint_name', None)
            if constraint != 'rut_por_delegacion':
                raise
            form.add_error('rut', 'Este RUT ya está registrado en la delegación. Busque el registro existente.')
        else:
            messages.success(request, 'Datos del vecino guardados.')
            return redirect('vecinos')
    return render(request, 'form.html', {'form': form, 'titulo': 'Editar vecino' if pk else 'Registrar vecino'})

@login_required
def solicitudes(request):
    qs = request.user.scope(Solicitud.objects.select_related('vecino', 'delegacion', 'responsable'))
    estado = request.GET.get('estado', '')
    if estado in Solicitud.Estado.values:
        qs = qs.filter(estado=estado)
    from django.core.paginator import Paginator
    return render(request, 'solicitudes.html', {'pagina': Paginator(qs, 20).get_page(request.GET.get('page')),
                                               'estados': Solicitud.Estado.choices, 'estado': estado})

@login_required
def solicitud_crear(request):
    form = SolicitudForm(request.POST if request.method == 'POST' else None, usuario=request.user)
    if request.method == 'POST' and form.is_valid():
        solicitud = crear_solicitud(request.user, **form.cleaned_data)
        messages.success(request, 'Solicitud ingresada.')
        return redirect('solicitud_detalle', pk=solicitud.pk)
    return render(request, 'form.html', {'form': form, 'titulo': 'Ingresar solicitud'})

def siguiente(usuario, solicitud):
    if solicitud.estado == 'ingresada' and usuario.supervisa:
        return 'asignada'
    if solicitud.estado == 'resuelta' and usuario.supervisa:
        return 'cerrada'
    if usuario.supervisa or solicitud.responsable_id == usuario.pk:
        return {'asignada': 'atencion', 'atencion': 'resuelta'}.get(solicitud.estado)
    return None

@login_required
def solicitud_detalle(request, pk):
    solicitud = get_object_or_404(request.user.scope(Solicitud.objects.select_related('vecino', 'delegacion', 'responsable')), pk=pk)
    return detalle_response(request, solicitud)

def detalle_response(request, solicitud, form=None, observacion=None, status=200):
    nuevo = siguiente(request.user, solicitud)
    if form is None:
        form = TransicionForm(solicitud=solicitud, nuevo=nuevo) if nuevo else None
    return render(request, 'detalle.html', {'solicitud': solicitud, 'transicion': form,
                 'accion': dict(Solicitud.Estado.choices).get(nuevo), 'observacion': observacion or ObservacionForm(),
                 'cambios': solicitud.cambios.select_related('actor'),
                 'observaciones': solicitud.observaciones.select_related('autor')}, status=status)

@login_required
@require_POST
def solicitud_transicion(request, pk):
    solicitud = get_object_or_404(request.user.scope(Solicitud.objects.all()), pk=pk)
    nuevo = siguiente(request.user, solicitud)
    if not nuevo:
        raise PermissionDenied
    form = TransicionForm(request.POST, solicitud=solicitud, nuevo=nuevo)
    if form.is_valid():
        try:
            transicionar(request.user, pk, form.cleaned_data['esperado'], form.cleaned_data['nuevo'],
                          form.cleaned_data['motivo'], getattr(form.cleaned_data['responsable'], 'pk', None))
            messages.success(request, 'Estado actualizado y registrado en el historial.')
        except ValidationError as error:
            form.add_error(None, error)
            return detalle_response(request, solicitud, form=form, status=409)
    else:
        return detalle_response(request, solicitud, form=form, status=400)
    return redirect('solicitud_detalle', pk=pk)

@login_required
@require_POST
def solicitud_observacion(request, pk):
    solicitud = get_object_or_404(request.user.scope(Solicitud.objects.all()), pk=pk)
    form = ObservacionForm(request.POST)
    if form.is_valid():
        try:
            agregar_observacion(request.user, pk, form.cleaned_data['texto'])
            messages.success(request, 'Observación registrada.')
        except ValidationError as error:
            form.add_error(None, error)
            return detalle_response(request, solicitud, observacion=form, status=409)
    else:
        return detalle_response(request, solicitud, observacion=form, status=400)
    return redirect('solicitud_detalle', pk=pk)

@login_required
def auditoria(request):
    if not request.user.administra:
        raise PermissionDenied
    from django.core.paginator import Paginator
    return render(request, 'auditoria.html', {'pagina': Paginator(Evento.objects.select_related('actor'), 30).get_page(request.GET.get('page'))})

````


## config/wsgi.py

````
import os
from django.core.wsgi import get_wsgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
application = get_wsgi_application()

````


## deploy/ec2/municipales-renew.service

````
[Unit]
Description=Renovación del certificado IP de Delegaciones Municipales
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=ec2-user
WorkingDirectory=/home/ec2-user/Delegaciones-Municipales
ExecStart=/usr/bin/bash /home/ec2-user/Delegaciones-Municipales/scripts/ec2.sh renew

````


## deploy/ec2/municipales-renew.timer

````
[Unit]
Description=Comprobar renovación de certificado IP cada doce horas

[Timer]
OnCalendar=*-*-* 00,12:00:00
RandomizedDelaySec=1h
Persistent=true
Unit=municipales-renew.service

[Install]
WantedBy=timers.target

````


## deploy/ec2/nginx-http.conf.template

````
# Bootstrap: only HTTP-01 challenges are served before a valid certificate exists.
server_tokens off;
server {
    listen 80 default_server;
    server_name _;
    return 404;
}
server {
    listen 80;
    server_name __PUBLIC_IP__;
    server_tokens off;
    location ^~ /.well-known/acme-challenge/ {
        root /var/www/acme;
        try_files $uri =404;
    }
    location / {
        return 503;
    }
}

````


## deploy/ec2/nginx-https.conf.template

````
server_tokens off;
server {
    listen 80 default_server;
    server_name _;
    return 404;
}
server {
    listen 80;
    server_name __PUBLIC_IP__;
    server_tokens off;
    location ^~ /.well-known/acme-challenge/ {
        root /var/www/acme;
        try_files $uri =404;
    }
    location / {
        return 301 https://__PUBLIC_IP__$request_uri;
    }
}
server {
    listen 443 ssl default_server;
    server_name __PUBLIC_IP__;
    server_tokens off;
    ssl_certificate /etc/letsencrypt/live/municipal-ip/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/municipal-ip/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_session_cache shared:TLS:10m;
    if ($host != "__PUBLIC_IP__") { return 404; }
    client_max_body_size 1m;
    location /static/ {
        alias /var/www/static/;
        add_header X-Content-Type-Options nosniff always;
    }
    location / {
        proxy_pass http://web:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header Connection "";
        proxy_http_version 1.1;
        proxy_read_timeout 35s;
    }
}

````


## manage.py

````
#!/usr/bin/env python
import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
from django.core.management import execute_from_command_line
execute_from_command_line(sys.argv)

````


## requirements-dev.txt

````
-r requirements.txt
playwright==1.63.0

````


## requirements-prod.lock

````
asgiref==3.12.1 \
    --hash=sha256:59dcb51c272ad209d59bed5708a64a333083e86017d7fcdd67498eeab7784340 \
    --hash=sha256:fe386d1c2bff7259ea95929266d12a8cf9a8b5a1c2598402967d8792e7a7c094
    # via
    #   -r requirements.txt
    #   django
    #   django-axes
django==5.2.18 \
    --hash=sha256:461c5dd06d2ea16bd5ca37d3f46e4def1d6b0fe7588c6f4e2119517bb0af8b2d \
    --hash=sha256:92ed81d500be6408ecd704d7bd1366c534f30427bffcc63c5fefb129561aec7c
    # via
    #   -r requirements.txt
    #   django-axes
django-axes==7.1.0 \
    --hash=sha256:0d73f2a5240ec6c03a1b343c0dd1bd0e6278ce181eaa700cf185536313c10df1 \
    --hash=sha256:e56edc4ba7eeebb3f30af3b59301db0a9880514eabc1e64f98b5fe5057829bfa
    # via -r requirements.txt
gunicorn==26.2.0 \
    --hash=sha256:62b864895d9ebff0b2f9867ba04fe811c93121596540830c9c916d0769668447 \
    --hash=sha256:bd249d0b3f7972f7432f0a6b6ff3b3ee2d129f70cd1ff6c09a9dd9e29a2b88e3
    # via -r requirements-prod.txt
psycopg==3.2.13 \
    --hash=sha256:309adaeda61d44556046ec9a83a93f42bbe5310120b1995f3af49ab6d9f13c1d \
    --hash=sha256:a481374514f2da627157f767a9336705ebefe93ea7a0522a6cbacba165da179a
    # via -r requirements.txt
psycopg-binary==3.2.13 \
    --hash=sha256:00ac1f1832c11ebf7ce3e30cd9cd9ec4d32b7d4aabe02e5cc6dca1b6ecff215d \
    --hash=sha256:028b49eb465f5d263d250cfd4f168fdabb306d0bbd97fd66a8a1fd7b696a953c \
    --hash=sha256:082579f2ae41bdabe20c82810810f3e290ac2206cccf0cb41cf36b3218f53b3c \
    --hash=sha256:087acf2b24787ae206718136c1f51bc90cda68b02c3819b0556f418e3565f2c3 \
    --hash=sha256:090c22795969ee1ace17322b1718769694607d942cef084c6fb4493adfa57da0 \
    --hash=sha256:0ef8ed4a4e0f7bf5e941782478a43c14b2b585b031e2266dd3afb87be2775d95 \
    --hash=sha256:13e2f8894d410678529ff9f1211f96c5a93ff142f992b302682b42d924428b61 \
    --hash=sha256:1c9e7ddbb1fe0c99ebe73e4658722d6e6fb7058dacac0fbe98653cf01a7a6871 \
    --hash=sha256:1db11a7e618d58cfb937c409c7d279a84cbb31d32a7efc63f1e5f426f3613793 \
    --hash=sha256:223fc610a80bbc4355ad3c9952d468a18bb5cd7065846a8c275f100d80cd4004 \
    --hash=sha256:27150515de5f709e4142429db6fd36a1d01f0b8b17d915b5f7bb095364465398 \
    --hash=sha256:2d45bc5f4335498d32a26c8f8c0bf9ce8c973c19e78a9ee77c031300fb361300 \
    --hash=sha256:2f63868cc96bc18486cebec24445affbdd7f7debf28fac466ea935a8b5a4753b \
    --hash=sha256:38cadba35c8e3d0a43a916457c9b91c510be7253576d052d9549fd3c49c55782 \
    --hash=sha256:4150a5e72f863be442d153829724109d83a76871d9bc801d6bb5b9c84b5b19b9 \
    --hash=sha256:4a6cafabdc0bfa37e11c6f365020fd5916b62d6296df581f4dceaa43a2ce680c \
    --hash=sha256:502a778c3e07c6b3aabfa56ee230e8c264d2debfab42d11535513a01bdfff0d6 \
    --hash=sha256:5056e701ec81e792f6acd362276585ac0c24456519b5e2fe552f298a04d2cd0c \
    --hash=sha256:532ea34f673148d637be65a96251832252e278540b39fbd683ef37e58ec361c1 \
    --hash=sha256:594dfbca3326e997ae738d3d339004e8416b1f7390f52ce8dc2d692393e8fa96 \
    --hash=sha256:596176ae3dfbf56fc61108870bfe17c7205d33ac28d524909feb5335201daa0a \
    --hash=sha256:5c77f156c7316529ed371b5f95a51139e531328ee39c37493a2afcbc1f79d5de \
    --hash=sha256:5d466ac3a3738647ff2405397946870dc363e33282ced151e7ea74f622947c06 \
    --hash=sha256:5f5081b2cbb0358bb3625109d41b57411bf9d9c29762a867e38c06d974b245ee \
    --hash=sha256:65df0d459ffba14082d8ca4bb2f6ffbb2f8d02968f7d34a747e1031934b76b23 \
    --hash=sha256:6a50db4661fae78779d3cc38a0a68cabc997ca9d485ec27443b109ef8ac1672a \
    --hash=sha256:6d8d1b709509d0f8cb857acf740b5eccd5bd2fb208a5b20e895f250519a32459 \
    --hash=sha256:6fe2982a73b2ea473c9e2b91a35a21af3b03313bed188eccbcde4972483ac60a \
    --hash=sha256:732b25c2d932ca0655ea2588563eae831dc0842c93c69be4754a5b0e9760b38d \
    --hash=sha256:7350d9cc4e35529c4548ddda34a1c17f28d3f3a8f792c25cd67e8a04952ed415 \
    --hash=sha256:7561a71d764d6f74d66e8b7d844b0f27fa33de508f65c17b1d56a94c73644776 \
    --hash=sha256:75ebc8335f48c339ec24f4c371595f6b7043147fe6d18e619c8564428ab8adaf \
    --hash=sha256:84c32892b75a3c7a1111b0ae17d567e161bec7f51b6419bfee6919973f57a811 \
    --hash=sha256:8b843c00478739e95c46d6d3472b13123b634685f107831a9bfc41503a06ecbd \
    --hash=sha256:8db77fac1dfe3f69c982db92a51fd78e1354fa8f523a6781a636123e5c7ffcde \
    --hash=sha256:8f1189dc78553ef4b2e55d9e116fc74870191bc6a9a5f4442412a703c4cc6c3b \
    --hash=sha256:915647b5bbbcde2bd464dc293eec4f74710fa71edc4f85aa6f6c8494a179dc9e \
    --hash=sha256:917ad1cd6e6ef8a9df2f28d7b29c7148f089be46ac56fe838f986c0227652d14 \
    --hash=sha256:9942255705255367d94368941e3a913b0daf74b47d191471dbe4dc0de9fbc769 \
    --hash=sha256:9ac329532f36342ff99fc1aefdbb531563bec03c7bc3ae934c8347a7a61339df \
    --hash=sha256:9b98ed605a394107ea624c3792896cef29b833d2e193facfd85ba72fc4e2f85b \
    --hash=sha256:9caf14745a1930b4e03fe4072cd7154eaf6e1241d20c42130ed784408a26b24b \
    --hash=sha256:9cfe87749d010dfd34534ba8c71aa0674db9a3fce65232c98989f77c742c9ce7 \
    --hash=sha256:9e25eb65494955c0dabdcd7097b004cbd70b982cf3cbc7186c2e854f788677a9 \
    --hash=sha256:a146f0a59a7e3ca92996f8133b1d5e5922e668f7c656b4a9201e702f4cf25896 \
    --hash=sha256:a56a8b1794cbf27ca04012ac2890d58cfc82b3b310c1dac4fa78fbf6f57e7440 \
    --hash=sha256:ac92d6bc1d4a41c7459953a9aa727b9966e937e94c9e072527317fd2a67d488b \
    --hash=sha256:b53b0d9499805b307017070492189e349256e0946f62c815e442baa01f2ea6c5 \
    --hash=sha256:b67f06a68d68b4621b6a411f9e583df876977afa06b1ba270b1b347d40aa93fc \
    --hash=sha256:c96cb5a27e68acac6d74b64fca38592a692de9c4b7827339190698d58027aa45 \
    --hash=sha256:cbbac4cd5b0e14b91ad8244268ca3fc2f527d1a337b489af57d7669c9d2e1a24 \
    --hash=sha256:cc3a0408435dfbb77eeca5e8050df4b19a6e9b7e5e5583edf524c4a83d6293b2 \
    --hash=sha256:d3aec6e2f1cf4deb1b9a3ac287c0591479f3bd851d0a911d628f8c2c71c14f4a \
    --hash=sha256:dbae6ab1966e2b61d97e47220556c330c4608bb4cfb3a124aa0595c39995c068 \
    --hash=sha256:de06fc9707a49f7c081b5c950974dd6de3dc33d681f7524f0b396471f5a4a480 \
    --hash=sha256:ea2fdbcc9142933a47c66970e0df8b363e3bd1ea4c5ce376f2f3d94a9aeec847 \
    --hash=sha256:ef324695327681c756e206fbd0aa9bbc50fd05f45c74bc97c640c13ba36cc108 \
    --hash=sha256:f062d725898bf6fc5cfc6349a0d08ee09f129deb14d7fcd5c30f9f1b349f39dc \
    --hash=sha256:f26f7009375cf1e92180e5c517c52da1054f7e690dde90e0ed00fa8b5736bcd4 \
    --hash=sha256:fae933e4564386199fc54845d85413eedb49760e0bcd2b621fde2dd1825b99b3 \
    --hash=sha256:fbc7c46da9b0db8126f8ebcdcc966c0a14e87c187af7978b47f6971bfbb9cc2c \
    --hash=sha256:ff7df7bd8ec2c805f3a4896b8ade971139af0f9f8cf45d05014ac71fe54887be
    # via -r requirements.txt
sqlparse==0.6.0 \
    --hash=sha256:113c35c75365ab9cc9c7231d68c6428fb11c085fc8e9eb1ad659b7ddbf6cd2b9 \
    --hash=sha256:b861c0288ce2fa56209a9a6412d2e066ac664b3873b89c26c9d8415e8e32996f
    # via
    #   -r requirements.txt
    #   django
typing-extensions==4.16.0 \
    --hash=sha256:481caa481374e813c1b176ada14e97f1f67a4539ce9cfeb3f350d78d6370c2e8 \
    --hash=sha256:dc983d19a509c94dba722ee6abd33940f7c05a89e243c47e907eb4db6f1a43e5
    # via
    #   -r requirements.txt
    #   psycopg

````


## requirements-prod.txt

````
-r requirements.txt
gunicorn==26.2.0

````


## requirements.lock

````
asgiref==3.12.1 \
    --hash=sha256:59dcb51c272ad209d59bed5708a64a333083e86017d7fcdd67498eeab7784340 \
    --hash=sha256:fe386d1c2bff7259ea95929266d12a8cf9a8b5a1c2598402967d8792e7a7c094
    # via
    #   -r requirements.txt
    #   django
    #   django-axes
django==5.2.18 \
    --hash=sha256:461c5dd06d2ea16bd5ca37d3f46e4def1d6b0fe7588c6f4e2119517bb0af8b2d \
    --hash=sha256:92ed81d500be6408ecd704d7bd1366c534f30427bffcc63c5fefb129561aec7c
    # via
    #   -r requirements.txt
    #   django-axes
django-axes==7.1.0 \
    --hash=sha256:0d73f2a5240ec6c03a1b343c0dd1bd0e6278ce181eaa700cf185536313c10df1 \
    --hash=sha256:e56edc4ba7eeebb3f30af3b59301db0a9880514eabc1e64f98b5fe5057829bfa
    # via -r requirements.txt
psycopg==3.2.13 \
    --hash=sha256:309adaeda61d44556046ec9a83a93f42bbe5310120b1995f3af49ab6d9f13c1d \
    --hash=sha256:a481374514f2da627157f767a9336705ebefe93ea7a0522a6cbacba165da179a
    # via -r requirements.txt
psycopg-binary==3.2.13 \
    --hash=sha256:00ac1f1832c11ebf7ce3e30cd9cd9ec4d32b7d4aabe02e5cc6dca1b6ecff215d \
    --hash=sha256:028b49eb465f5d263d250cfd4f168fdabb306d0bbd97fd66a8a1fd7b696a953c \
    --hash=sha256:082579f2ae41bdabe20c82810810f3e290ac2206cccf0cb41cf36b3218f53b3c \
    --hash=sha256:087acf2b24787ae206718136c1f51bc90cda68b02c3819b0556f418e3565f2c3 \
    --hash=sha256:090c22795969ee1ace17322b1718769694607d942cef084c6fb4493adfa57da0 \
    --hash=sha256:0ef8ed4a4e0f7bf5e941782478a43c14b2b585b031e2266dd3afb87be2775d95 \
    --hash=sha256:13e2f8894d410678529ff9f1211f96c5a93ff142f992b302682b42d924428b61 \
    --hash=sha256:1c9e7ddbb1fe0c99ebe73e4658722d6e6fb7058dacac0fbe98653cf01a7a6871 \
    --hash=sha256:1db11a7e618d58cfb937c409c7d279a84cbb31d32a7efc63f1e5f426f3613793 \
    --hash=sha256:223fc610a80bbc4355ad3c9952d468a18bb5cd7065846a8c275f100d80cd4004 \
    --hash=sha256:27150515de5f709e4142429db6fd36a1d01f0b8b17d915b5f7bb095364465398 \
    --hash=sha256:2d45bc5f4335498d32a26c8f8c0bf9ce8c973c19e78a9ee77c031300fb361300 \
    --hash=sha256:2f63868cc96bc18486cebec24445affbdd7f7debf28fac466ea935a8b5a4753b \
    --hash=sha256:38cadba35c8e3d0a43a916457c9b91c510be7253576d052d9549fd3c49c55782 \
    --hash=sha256:4150a5e72f863be442d153829724109d83a76871d9bc801d6bb5b9c84b5b19b9 \
    --hash=sha256:4a6cafabdc0bfa37e11c6f365020fd5916b62d6296df581f4dceaa43a2ce680c \
    --hash=sha256:502a778c3e07c6b3aabfa56ee230e8c264d2debfab42d11535513a01bdfff0d6 \
    --hash=sha256:5056e701ec81e792f6acd362276585ac0c24456519b5e2fe552f298a04d2cd0c \
    --hash=sha256:532ea34f673148d637be65a96251832252e278540b39fbd683ef37e58ec361c1 \
    --hash=sha256:594dfbca3326e997ae738d3d339004e8416b1f7390f52ce8dc2d692393e8fa96 \
    --hash=sha256:596176ae3dfbf56fc61108870bfe17c7205d33ac28d524909feb5335201daa0a \
    --hash=sha256:5c77f156c7316529ed371b5f95a51139e531328ee39c37493a2afcbc1f79d5de \
    --hash=sha256:5d466ac3a3738647ff2405397946870dc363e33282ced151e7ea74f622947c06 \
    --hash=sha256:5f5081b2cbb0358bb3625109d41b57411bf9d9c29762a867e38c06d974b245ee \
    --hash=sha256:65df0d459ffba14082d8ca4bb2f6ffbb2f8d02968f7d34a747e1031934b76b23 \
    --hash=sha256:6a50db4661fae78779d3cc38a0a68cabc997ca9d485ec27443b109ef8ac1672a \
    --hash=sha256:6d8d1b709509d0f8cb857acf740b5eccd5bd2fb208a5b20e895f250519a32459 \
    --hash=sha256:6fe2982a73b2ea473c9e2b91a35a21af3b03313bed188eccbcde4972483ac60a \
    --hash=sha256:732b25c2d932ca0655ea2588563eae831dc0842c93c69be4754a5b0e9760b38d \
    --hash=sha256:7350d9cc4e35529c4548ddda34a1c17f28d3f3a8f792c25cd67e8a04952ed415 \
    --hash=sha256:7561a71d764d6f74d66e8b7d844b0f27fa33de508f65c17b1d56a94c73644776 \
    --hash=sha256:75ebc8335f48c339ec24f4c371595f6b7043147fe6d18e619c8564428ab8adaf \
    --hash=sha256:84c32892b75a3c7a1111b0ae17d567e161bec7f51b6419bfee6919973f57a811 \
    --hash=sha256:8b843c00478739e95c46d6d3472b13123b634685f107831a9bfc41503a06ecbd \
    --hash=sha256:8db77fac1dfe3f69c982db92a51fd78e1354fa8f523a6781a636123e5c7ffcde \
    --hash=sha256:8f1189dc78553ef4b2e55d9e116fc74870191bc6a9a5f4442412a703c4cc6c3b \
    --hash=sha256:915647b5bbbcde2bd464dc293eec4f74710fa71edc4f85aa6f6c8494a179dc9e \
    --hash=sha256:917ad1cd6e6ef8a9df2f28d7b29c7148f089be46ac56fe838f986c0227652d14 \
    --hash=sha256:9942255705255367d94368941e3a913b0daf74b47d191471dbe4dc0de9fbc769 \
    --hash=sha256:9ac329532f36342ff99fc1aefdbb531563bec03c7bc3ae934c8347a7a61339df \
    --hash=sha256:9b98ed605a394107ea624c3792896cef29b833d2e193facfd85ba72fc4e2f85b \
    --hash=sha256:9caf14745a1930b4e03fe4072cd7154eaf6e1241d20c42130ed784408a26b24b \
    --hash=sha256:9cfe87749d010dfd34534ba8c71aa0674db9a3fce65232c98989f77c742c9ce7 \
    --hash=sha256:9e25eb65494955c0dabdcd7097b004cbd70b982cf3cbc7186c2e854f788677a9 \
    --hash=sha256:a146f0a59a7e3ca92996f8133b1d5e5922e668f7c656b4a9201e702f4cf25896 \
    --hash=sha256:a56a8b1794cbf27ca04012ac2890d58cfc82b3b310c1dac4fa78fbf6f57e7440 \
    --hash=sha256:ac92d6bc1d4a41c7459953a9aa727b9966e937e94c9e072527317fd2a67d488b \
    --hash=sha256:b53b0d9499805b307017070492189e349256e0946f62c815e442baa01f2ea6c5 \
    --hash=sha256:b67f06a68d68b4621b6a411f9e583df876977afa06b1ba270b1b347d40aa93fc \
    --hash=sha256:c96cb5a27e68acac6d74b64fca38592a692de9c4b7827339190698d58027aa45 \
    --hash=sha256:cbbac4cd5b0e14b91ad8244268ca3fc2f527d1a337b489af57d7669c9d2e1a24 \
    --hash=sha256:cc3a0408435dfbb77eeca5e8050df4b19a6e9b7e5e5583edf524c4a83d6293b2 \
    --hash=sha256:d3aec6e2f1cf4deb1b9a3ac287c0591479f3bd851d0a911d628f8c2c71c14f4a \
    --hash=sha256:dbae6ab1966e2b61d97e47220556c330c4608bb4cfb3a124aa0595c39995c068 \
    --hash=sha256:de06fc9707a49f7c081b5c950974dd6de3dc33d681f7524f0b396471f5a4a480 \
    --hash=sha256:ea2fdbcc9142933a47c66970e0df8b363e3bd1ea4c5ce376f2f3d94a9aeec847 \
    --hash=sha256:ef324695327681c756e206fbd0aa9bbc50fd05f45c74bc97c640c13ba36cc108 \
    --hash=sha256:f062d725898bf6fc5cfc6349a0d08ee09f129deb14d7fcd5c30f9f1b349f39dc \
    --hash=sha256:f26f7009375cf1e92180e5c517c52da1054f7e690dde90e0ed00fa8b5736bcd4 \
    --hash=sha256:fae933e4564386199fc54845d85413eedb49760e0bcd2b621fde2dd1825b99b3 \
    --hash=sha256:fbc7c46da9b0db8126f8ebcdcc966c0a14e87c187af7978b47f6971bfbb9cc2c \
    --hash=sha256:ff7df7bd8ec2c805f3a4896b8ade971139af0f9f8cf45d05014ac71fe54887be
    # via -r requirements.txt
sqlparse==0.6.0 \
    --hash=sha256:113c35c75365ab9cc9c7231d68c6428fb11c085fc8e9eb1ad659b7ddbf6cd2b9 \
    --hash=sha256:b861c0288ce2fa56209a9a6412d2e066ac664b3873b89c26c9d8415e8e32996f
    # via
    #   -r requirements.txt
    #   django
typing-extensions==4.16.0 \
    --hash=sha256:481caa481374e813c1b176ada14e97f1f67a4539ce9cfeb3f350d78d6370c2e8 \
    --hash=sha256:dc983d19a509c94dba722ee6abd33940f7c05a89e243c47e907eb4db6f1a43e5
    # via
    #   -r requirements.txt
    #   psycopg

````


## requirements.txt

````
asgiref==3.12.1
django==5.2.18
django-axes==7.1.0
psycopg==3.2.13
psycopg-binary==3.2.13
sqlparse==0.6.0
typing-extensions==4.16.0

````


## scripts/certificado_local.py

````
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

````


## scripts/check_accessibility.py

````
"""Run local axe-core checks; pass its verified local JS path as argument."""
import json
from pathlib import Path
import sys
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
credentials = json.loads((ROOT / '.local/demo-credentials.json').read_text())
axe = Path(sys.argv[1]).resolve()
results = []
routes = ['/acceso/', '/', '/vecinos/', '/vecinos/nuevo/', '/solicitudes/', '/solicitudes/nueva/', '/solicitudes/1/',
          '/agenda/', '/agenda/nueva/', '/reportes/']
result_file = ROOT / '.local/browser/sprint-2.json'
if result_file.exists():
    result = json.loads(result_file.read_text())
    routes.append(f"/agenda/{result['cita_programada']}/")
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
    for width in [1440, 768]:
        context = browser.new_context(viewport={'width': width, 'height': 1024})
        page = context.new_page()
        for route in routes:
            page.goto('http://127.0.0.1:8000' + route)
            if route == '/':
                page.locator('#id_username').fill('delegado.norte')
                page.locator('#id_password').fill(credentials['delegado.norte'])
                page.get_by_role('button', name='Ingresar al sistema').click()
                page.wait_for_url('http://127.0.0.1:8000/')
            page.add_script_tag(path=str(axe))
            audit = page.evaluate("async () => await axe.run(document, {runOnly: {type: 'tag', values: ['wcag2a','wcag2aa','wcag21aa']}})")
            overflow = page.evaluate('document.documentElement.scrollWidth > window.innerWidth')
            results.append({'width': width, 'route': route, 'horizontal_overflow': overflow,
                            'violations': [{'id': v['id'], 'impact': v['impact'],
                                            'targets': [node['target'] for node in v['nodes']]} for v in audit['violations']],
                            'manual_checks_required': [v['id'] for v in audit['incomplete']]})
        context.close()
    browser.close()
output = ROOT / '.local/browser/accessibility.json'
output.parent.mkdir(exist_ok=True)
output.write_text(json.dumps(results, indent=2))
for result in results:
    print(f"{result['width']} {result['route']}: {len(result['violations'])} infracciones, desborde={result['horizontal_overflow']}")
if any(result['violations'] or result['horizontal_overflow'] for result in results):
    raise SystemExit(1)
print('Sin infracciones automáticas en las vistas verificadas; la revisión humana sigue pendiente.')

````


## scripts/check_ec2.py

````
"""Verify private Gunicorn readiness without publishing its port."""
from urllib.request import Request, urlopen

request = Request('http://127.0.0.1:8000/acceso/', headers={'X-Forwarded-Proto': 'https'})
with urlopen(request, timeout=3) as response:
    content = response.read().decode()
    if response.status != 200 or 'Ingresar al sistema' not in content or 'csrfmiddlewaretoken' not in content:
        raise SystemExit('El acceso de la aplicación aún no está disponible.')

````


## scripts/check_ready.py

````
"""A health check must confirm a functional login form, not only an open port."""
from urllib.request import urlopen
import os
from pathlib import Path
import ssl

tls = os.environ.get('LOCAL_HTTPS') == 'true'
context = ssl.create_default_context(cafile=str(Path(__file__).resolve().parent.parent / '.local/tls/localhost.crt')) if tls else None
scheme = 'https' if tls else 'http'
with urlopen(f'{scheme}://127.0.0.1:8000/acceso/', timeout=3, context=context) as response:
    page = response.read().decode()
    if response.status != 200 or 'Ingresar al sistema' not in page or 'csrfmiddlewaretoken' not in page:
        raise SystemExit('El formulario de acceso aún no está disponible.')

````


## scripts/demo.py

````
"""Create fictional demonstration data once; preserve existing accounts."""
import json
import os
from pathlib import Path
import secrets
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.db import transaction
from apps.cuentas.models import Usuario
from apps.delegaciones.models import Delegacion
from apps.vecinos.models import Vecino
from apps.solicitudes.services import crear_solicitud

credentials_path = ROOT / '.local' / 'demo-credentials.json'
credentials = json.loads(credentials_path.read_text()) if credentials_path.exists() else {}
with transaction.atomic():
    norte, _ = Delegacion.objects.get_or_create(nombre='Delegación Norte (Demo)', defaults={'direccion': 'Avenida Ejemplo 100'})
    sur, _ = Delegacion.objects.get_or_create(nombre='Delegación Sur (Demo)', defaults={'direccion': 'Calle Ficticia 200'})
    for username, role, delegation in [
        ('admin.demo', 'administrador', None), ('delegado.norte', 'delegado', norte),
        ('funcionario.norte', 'funcionario', norte), ('funcionario.sur', 'funcionario', sur),
    ]:
        if not Usuario.objects.filter(username=username).exists():
            password = secrets.token_urlsafe(18)
            user = Usuario(username=username, rol=role, delegacion=delegation,
                           is_staff=role == 'administrador', is_superuser=role == 'administrador')
            user.set_password(password)
            user.full_clean()
            user.save()
            credentials[username] = password
    vecino, _ = Vecino.objects.get_or_create(delegacion=norte, rut='12345678-5', defaults={
        'nombre': 'Vecina de Ejemplo', 'email': 'vecina@example.invalid', 'direccion': 'Pasaje Ficticio 10'})
    if not vecino.solicitud_set.exists():
        crear_solicitud(Usuario.objects.get(username='funcionario.norte'), vecino, 'reclamo',
                       'Ejemplo ficticio: solicitar revisión de luminaria en una plaza.')
fd = os.open(credentials_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(fd, 'w') as stream:
    json.dump(credentials, stream, indent=2)
print('Datos ficticios preparados. Credenciales privadas en .local/demo-credentials.json; no compartir ni versionar.')

````


## scripts/ec2.sh

````
#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
test -f .local/ec2.env || { echo 'Ejecute primero scripts/prepare_ec2.py.' >&2; exit 1; }
dc() { docker compose --env-file .local/ec2.env -f compose.ec2.yaml "$@"; }
case "${1:-help}" in
  bootstrap)
    python3 scripts/render_ec2.py http
    dc up -d proxy
    ;;
  cert-test|cert-issue)
    public_ip=$(python3 scripts/ec2_config.py ip)
    acme_email=$(python3 scripts/ec2_config.py email)
    if [ "$1" = cert-test ]; then
      dc run --rm certbot certonly --webroot -w /var/www/acme \
        --ip-address "$public_ip" --cert-name municipal-ip-staging \
        --required-profile shortlived --preferred-challenges http \
        --email "$acme_email" --agree-tos --non-interactive --test-cert
    else
      dc run --rm certbot certonly --webroot -w /var/www/acme \
        --ip-address "$public_ip" --cert-name municipal-ip \
        --required-profile shortlived --preferred-challenges http \
        --email "$acme_email" --agree-tos --non-interactive
    fi
    ;;
  activate)
    dc run --rm --entrypoint sh certbot -c \
      'test -s /etc/letsencrypt/live/municipal-ip/fullchain.pem && test -s /etc/letsencrypt/live/municipal-ip/privkey.pem'
    dc up --build --wait -d web
    python3 scripts/render_ec2.py https
    if ! dc run --rm --no-deps proxy -t; then
      python3 scripts/render_ec2.py http
      echo 'Nginx rechazó la configuración HTTPS; se restauró el archivo HTTP de preparación.' >&2
      exit 1
    fi
    dc up -d proxy
    dc exec -T proxy nginx -s reload
    ;;
  renew)
    dc run --rm certbot renew --cert-name municipal-ip --non-interactive --quiet
    dc exec -T proxy nginx -t
    dc exec -T proxy nginx -s reload
    ;;
  status)
    dc ps -a
    ;;
  down)
    dc down
    ;;
  *)
    echo 'Uso: sh scripts/ec2.sh bootstrap|cert-test|cert-issue|activate|renew|status|down'
    exit 1
    ;;
esac

````


## scripts/ec2_config.py

````
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

````


## scripts/export_codigo.py

````
"""Export all project-owned source files as a readable HTML review, without secrets."""
from html import escape
from pathlib import Path

root = Path(__file__).resolve().parent.parent
directories = ['apps', 'config', 'deploy', 'scripts', 'static', 'templates']
names = ['manage.py', 'Dockerfile', 'compose.yaml', 'compose.https.yaml',
         '.dockerignore', '.gitignore', 'requirements.txt', 'requirements.lock',
         'requirements-dev.txt', 'Dockerfile.ec2', 'compose.ec2.yaml',
         'requirements-prod.txt', 'requirements-prod.lock']
paths = [root / name for name in names]
for name in directories:
    paths.extend(p for p in (root / name).rglob('*')
                 if p.is_file() and '__pycache__' not in p.parts
                 and p.suffix in {'.py', '.sh', '.html', '.css', '.js', '.template', '.service', '.timer'})
paths = sorted(set(paths))
body = ['<!doctype html><html lang="es"><meta charset="utf-8">',
        '<title>Revisión del código completo</title>',
        '<style>body{font:16px sans-serif;max-width:1200px;margin:auto;padding:24px}'
        'pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f5f6;padding:16px}'
        'a{line-height:1.8}</style><h1>Código completo para revisión</h1>',
        '<p>Incluye código propio, pruebas, migraciones y configuración pública. '
        'Excluye credenciales, datos privados y binarios de dependencias de terceros.</p><ol>']
for index, path in enumerate(paths):
    body.append(f'<li><a href="#f{index}">{escape(str(path.relative_to(root)))}</a></li>')
body.append('</ol>')
for index, path in enumerate(paths):
    if path.is_symlink():
        raise SystemExit('No se exportan enlaces simbólicos.')
    body.append(f'<h2 id="f{index}">{escape(str(path.relative_to(root)))}</h2>'
                f'<pre><code>{escape(path.read_text())}</code></pre>')
body.append('</html>')
target = root / 'docs/codigo-completo.html'
target.write_text('\n'.join(body))
markdown = ['# Código completo para revisión\n',
            'Código propio completo, pruebas, migraciones y configuración pública. '
            'Sin credenciales ni binarios de terceros.\n']
for path in paths:
    markdown.append(f'\n## {path.relative_to(root)}\n\n````\n{path.read_text()}\n````\n')
(root / 'docs/codigo-completo.md').write_text('\n'.join(markdown))
print(f'Código exportado: {len(paths)} archivos completos; sin configuración privada.')

````


## scripts/export_evidencias.py

````
"""Create a PDF containing the real screenshots of the second increment."""
import base64
import html
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'docs/evidencias'
OUT.mkdir(exist_ok=True)
screens = [('agenda-pc.png', 'Agenda de atenciones · PC'),
           ('atencion-tablet.png', 'Detalle de atención · Tablet'),
           ('reportes-pc.png', 'Reportes de solicitudes · PC'),
           ('reportes-tablet.png', 'Reportes de solicitudes · Tablet')]
sections = []
for filename, title in screens:
    data = (ROOT / '.local/browser' / filename).read_bytes()
    (OUT / filename).write_bytes(data)
    image = base64.b64encode(data).decode('ascii')
    sections.append(f'<section><h1>{html.escape(title)}</h1><p>Prototipo académico · Datos ficticios</p>'
                    f'<img alt="{html.escape(title)}" src="data:image/png;base64,{image}"></section>')
document = '''<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Agenda y reportes municipales</title>
<style>@page{size:A4 landscape;margin:8mm}body{margin:0;font-family:Arial,sans-serif;color:#163044}section{break-after:page}section:last-child{break-after:auto}h1{font-size:16px;margin:0 0 4px}p{font-size:11px;margin:0 0 6px}img{display:block;max-width:100%;max-height:175mm;margin:auto;object-fit:contain}</style></head><body>'''
document += ''.join(sections) + '</body></html>'
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox'])
    page = browser.new_page()
    page.set_content(document)
    page.locator('img').evaluate_all('(images) => Promise.all(images.map(image => image.decode()))')
    page.pdf(path=str(OUT / 'agenda-y-reportes.pdf'), print_background=True, prefer_css_page_size=True)
    browser.close()
print('Creado docs/evidencias/agenda-y-reportes.pdf con capturas reales del incremento.')

````


## scripts/init_container.py

````
"""Initialize private development configuration in a persistent Docker volume."""
import json
import os
from pathlib import Path
import secrets

root = Path(__file__).resolve().parent.parent
local = root / '.local'
local.mkdir(exist_ok=True, mode=0o700)
config_file = local / 'config.json'
if not config_file.exists():
    values = {'DJANGO_SECRET_KEY': secrets.token_urlsafe(60), 'DJANGO_DEBUG': 'true',
              'POSTGRES_PASSWORD': secrets.token_urlsafe(32)}
    fd = os.open(config_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(values, stream)
values = json.loads(config_file.read_text())
password_file = local / 'postgres-password.txt'
if not password_file.exists():
    fd = os.open(password_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream:
        stream.write(values['POSTGRES_PASSWORD'])
elif not secrets.compare_digest(password_file.read_text(), values['POSTGRES_PASSWORD']):
    raise SystemExit('La configuración privada no coincide. Revise los volúmenes conservados sin eliminar sus datos.')
print('Configuración privada de desarrollo preparada; no se muestran credenciales.')

````


## scripts/init_ec2.py

````
"""Initialize distinct application and database-admin secrets without displaying them."""
import os
from pathlib import Path
import runpy
import secrets

root = Path(__file__).resolve().parent.parent
runpy.run_path(str(root / 'scripts/init_container.py'))
path = Path('/run/db-admin/password.txt')
if not path.exists():
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'w') as stream:
        stream.write(secrets.token_urlsafe(40))
print('Secretos de EC2 preparados en volúmenes separados; sin mostrar valores.')

````


## scripts/install.sh

````
#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
export UV_CACHE_DIR="$PWD/.local/uv-cache"
uv venv --allow-existing .venv
uv pip install --python .venv/bin/python --require-hashes -r requirements.lock
.venv/bin/python scripts/prepare.py
.venv/bin/python manage.py migrate --noinput
.venv/bin/python scripts/demo.py
.venv/bin/python manage.py check

````


## scripts/install_amazon_linux.sh

````
#!/bin/sh
# Run only on the user's authorized Amazon Linux 2023 instance.
set -eu
. /etc/os-release
if [ "$ID" != amzn ] || [ "$VERSION_ID" != 2023 ]; then
  echo 'Este instalador requiere Amazon Linux 2023.' >&2
  exit 1
fi
sudo dnf install -y docker python3 curl tar gzip
sudo systemctl enable --now docker
if ! docker compose version >/dev/null 2>&1; then
  compose_version=v2.39.4
  architecture=$(uname -m)
  case "$architecture" in x86_64|aarch64) ;; *) echo 'Arquitectura no soportada.' >&2; exit 1;; esac
  filename="docker-compose-linux-$architecture"
  task_tmp=$(mktemp -d)
  trap 'rm -rf "$task_tmp"' EXIT HUP INT TERM
  curl --fail --location --proto '=https' --tlsv1.2 \
    "https://github.com/docker/compose/releases/download/$compose_version/$filename" -o "$task_tmp/$filename"
  curl --fail --location --proto '=https' --tlsv1.2 \
    "https://github.com/docker/compose/releases/download/$compose_version/checksums.txt" -o "$task_tmp/checksums.txt"
  awk -v file="$filename" '{name=$2; sub(/^\*/, "", name); if (name == file) print}' "$task_tmp/checksums.txt" > "$task_tmp/selected.sha256"
  test -s "$task_tmp/selected.sha256"
  (cd "$task_tmp" && sha256sum --check --strict selected.sha256)
  sudo mkdir -p /usr/local/lib/docker/cli-plugins
  sudo install -m 0755 "$task_tmp/$filename" /usr/local/lib/docker/cli-plugins/docker-compose
fi
sudo usermod -aG docker ec2-user
echo 'Docker preparado. Salga de SSH y vuelva a ingresar para activar el grupo docker.'

````


## scripts/package.py

````
"""Create a reviewable source bundle without private configuration or databases."""
import hashlib
import os
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / 'dist'
DIST.mkdir(exist_ok=True)
target = DIST / 'Delegaciones-Municipales-demo.zip'
directories = {'apps', 'config', 'deploy', 'docs', 'scripts', 'static', 'templates', 'vendor'}
files = {'.gitignore', '.dockerignore', 'Dockerfile', 'compose.yaml', 'compose.https.yaml', 'manage.py', 'README.md',
         'requirements.txt', 'requirements.lock', 'requirements-dev.txt',
         'Dockerfile.ec2', 'compose.ec2.yaml', 'requirements-prod.txt', 'requirements-prod.lock'}
excluded = {'.git', '.local', '.venv', '__pycache__', 'dist', 'staticfiles'}

with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
    for directory, names, filenames in os.walk(ROOT):
        current = Path(directory)
        names[:] = sorted(name for name in names if name not in excluded and
                          (current != ROOT or name in directories))
        for filename in sorted(filenames):
            path = current / filename
            if current == ROOT and filename not in files:
                continue
            if filename.endswith(('.pyc', '.log')) or filename in {'.env', '.coverage'}:
                continue
            if path.is_symlink():
                raise SystemExit(f'No se incluyen enlaces simbólicos: {path.relative_to(ROOT)}')
            archive.write(path, Path('Delegaciones-Municipales') / path.relative_to(ROOT))

with zipfile.ZipFile(target) as archive:
    if archive.testzip() is not None:
        raise SystemExit('El paquete no superó la comprobación de integridad.')
    names = archive.namelist()
    if any(set(Path(name).parts) & excluded for name in names):
        raise SystemExit('El paquete contiene una ruta privada o generada no permitida.')
    if 'Delegaciones-Municipales/compose.yaml' not in names or not any('/vendor/wheels/' in name for name in names):
        raise SystemExit('Faltan archivos necesarios para ejecutar la demostración.')

digest = hashlib.sha256(target.read_bytes()).hexdigest()
(DIST / (target.name + '.sha256')).write_text(f'{digest}  {target.name}\n')
print(f'Paquete creado: {len(names)} archivos, {target.stat().st_size / 1024 / 1024:.1f} MiB; configuración privada excluida.')

````


## scripts/prepare.py

````
"""Prepare only a local development database; never print credentials."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import time

ROOT = Path(__file__).resolve().parent.parent
LOCAL = ROOT / '.local'
LOCAL.mkdir(exist_ok=True, mode=0o700)
path = LOCAL / 'config.json'
if not path.exists():
    values = {'DJANGO_SECRET_KEY': secrets.token_urlsafe(60), 'DJANGO_DEBUG': 'true',
              'POSTGRES_PASSWORD': secrets.token_urlsafe(32), 'POSTGRES_PORT': '55432'}
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(values, stream)
config = json.loads(path.read_text())
name = 'delegaciones-postgres-dev'
exists = subprocess.run(['docker', 'container', 'inspect', name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
if exists:
    subprocess.run(['docker', 'start', name], check=True, stdout=subprocess.DEVNULL)
else:
    docker_env = os.environ.copy()
    docker_env.update(POSTGRES_PASSWORD=config['POSTGRES_PASSWORD'], POSTGRES_USER='delegaciones', POSTGRES_DB='delegaciones')
    subprocess.run(['docker', 'run', '-d', '--name', name, '-p', '127.0.0.1:55432:5432',
                    '-e', 'POSTGRES_PASSWORD', '-e', 'POSTGRES_USER', '-e', 'POSTGRES_DB',
                    '-v', 'delegaciones-pgdata:/var/lib/postgresql/data',
                    'postgres:17@sha256:2d2b8998d31037bf721cfdf764d76ba74171b4fab3431b7f72c27c56ddbdf9e3'],
                   env=docker_env, check=True, stdout=subprocess.DEVNULL)
for attempt in range(30):
    ready = subprocess.run(['docker', 'exec', name, 'pg_isready', '-U', 'delegaciones', '-d', 'delegaciones'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if ready.returncode == 0:
        print('PostgreSQL local disponible. Configuración privada en .local/config.json.')
        break
    time.sleep(1)
else:
    raise SystemExit('PostgreSQL no respondió; revise el contenedor de desarrollo.')

````


## scripts/prepare_ec2.py

````
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

````


## scripts/provision_ec2.py

````
"""Provision a nonsuperuser application role; only this transient service sees admin secrets."""
import json
from pathlib import Path
import psycopg
from psycopg import sql

config = json.loads((Path(__file__).resolve().parent.parent / '.local/config.json').read_text())
with psycopg.connect(host='db', dbname='delegaciones', user='postgres',
                    password=Path('/run/db-admin/password.txt').read_text(), autocommit=True) as connection:
    with connection.cursor() as cursor:
        cursor.execute('SELECT rolsuper, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname=%s', ('delegaciones',))
        role = cursor.fetchone()
        if role is None:
            cursor.execute(sql.SQL('CREATE ROLE delegaciones LOGIN PASSWORD {}').format(sql.Literal(config['POSTGRES_PASSWORD'])))
        elif any(role):
            raise SystemExit('La cuenta de aplicación tiene privilegios administrativos inesperados. Revise sin borrar datos.')
        cursor.execute('ALTER DATABASE delegaciones OWNER TO delegaciones')
        cursor.execute('CREATE EXTENSION IF NOT EXISTS btree_gist')
with psycopg.connect(host='db', dbname='delegaciones', user='delegaciones',
                    password=config['POSTGRES_PASSWORD']):
    pass
print('Cuenta de aplicación sin superusuario preparada y autenticación verificada.')

````


## scripts/render_ec2.py

````
"""Render public Nginx configuration using a validated IPv4 address."""
import sys
from ec2_config import ROOT, read_config

mode = sys.argv[1]
if mode not in ('http', 'https'):
    raise SystemExit('Modo permitido: http o https.')
values = read_config()
template = (ROOT / f'deploy/ec2/nginx-{mode}.conf.template').read_text()
target = ROOT / '.local/ec2/nginx/default.conf'
target.write_text(template.replace('__PUBLIC_IP__', values['PUBLIC_IP']))
print('Configuración de Nginx preparada. El servidor requiere comprobación y recarga.')

````


## scripts/serve_https.py

````
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

````


## scripts/smoke_browser.py

````
"""Exercise the first sprint against a running local server using fictional data."""
import json
from pathlib import Path
import re
import uuid
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
credentials = json.loads((ROOT / '.local/demo-credentials.json').read_text())
BASE = 'http://127.0.0.1:8000'
OUT = ROOT / '.local/browser'
OUT.mkdir(exist_ok=True)

def login(browser, username, viewport):
    context = browser.new_context(viewport=viewport)
    page = context.new_page()
    page.goto(BASE + '/acceso/')
    page.locator('#id_username').fill(username)
    page.locator('#id_password').fill(credentials[username])
    page.get_by_role('button', name='Ingresar al sistema').click()
    page.wait_for_url(BASE + '/')
    return context, page

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
    context, page = login(browser, 'funcionario.norte', {'width': 1440, 'height': 1000})
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.screenshot(path=str(OUT / 'panel-pc.png'), full_page=True)
    page.get_by_role('link', name='Registrar vecino').click()
    page.locator('#id_rut').fill('11111111-1')
    page.locator('#id_nombre').fill('Vecino de Prueba Navegador')
    page.locator('#id_email').fill('prueba@example.invalid')
    page.locator('#id_direccion').fill('Dirección ficticia para pruebas')
    page.get_by_role('button', name='Guardar', exact=True).click()
    # Repeated runs may find the same fictional RUT already registered.
    if page.url.endswith('/vecinos/nuevo/'):
        assert page.locator('.errorlist').count() > 0
    page.goto(BASE + '/solicitudes/nueva/')
    page.locator('#id_vecino').select_option(label='Vecino de Prueba Navegador · 11111111-1')
    page.locator('#id_tipo').select_option('reclamo')
    description = 'Prueba navegador ' + uuid.uuid4().hex[:8] + ': luminaria ficticia.'
    page.locator('#id_descripcion').fill(description)
    page.get_by_role('button', name='Guardar', exact=True).click()
    page.wait_for_url(re.compile(r'/solicitudes/\d+/$'))
    url = page.url
    assert page.get_by_text(description, exact=True).is_visible()
    assert not page.get_by_role('button', name='Confirmar cambio de estado').count()

    delegate_context, delegate = login(browser, 'delegado.norte', {'width': 768, 'height': 1024})
    delegate.goto(url)
    delegate.locator('#id_responsable').select_option(label='funcionario.norte')
    delegate.locator('#id_motivo').fill('Asignación autorizada de prueba.')
    delegate.get_by_role('button', name='Confirmar cambio de estado').click()
    assert delegate.locator('.badge').inner_text() == 'Asignada'
    page.reload()
    page.locator('#id_motivo').fill('Inicio de atención de prueba.')
    page.get_by_role('button', name='Confirmar cambio de estado').click()
    assert page.locator('.badge').inner_text() == 'En atención'
    page.locator('#id_motivo').fill('Solución ficticia documentada.')
    page.get_by_role('button', name='Confirmar cambio de estado').click()
    assert page.locator('.badge').inner_text() == 'Resuelta'
    delegate.reload()
    delegate.locator('#id_motivo').fill('Verificación y cierre de prueba.')
    delegate.get_by_role('button', name='Confirmar cambio de estado').click()
    assert delegate.locator('.badge').inner_text() == 'Cerrada'
    assert delegate.locator('.timeline li').count() == 4
    assert delegate.locator('.note').count() == 4
    assert delegate.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    delegate.screenshot(path=str(OUT / 'solicitud-tablet.png'), full_page=True)

    other_context, other = login(browser, 'funcionario.sur', {'width': 1280, 'height': 900})
    response = other.goto(url)
    assert response.status == 404

    admin_context, admin = login(browser, 'admin.demo', {'width': 1440, 'height': 1000})
    admin.goto(BASE + '/auditoria/')
    assert admin.get_by_role('heading', name='Auditoría').is_visible()
    assert admin.get_by_text('solicitud.cerrada', exact=True).count() > 0
    admin.goto(BASE + '/admin/')
    assert admin.get_by_text('Administración municipal', exact=True).is_visible()

    page.get_by_role('button', name='Salir', exact=True).click()
    page.wait_for_url(BASE + '/acceso/')
    # Django focuses the username automatically on login. Shift+Tab reaches
    # the preceding skip link without relying on browser history focus.
    page.locator('#id_username').focus()
    page.keyboard.press('Shift+Tab')
    assert page.evaluate('document.activeElement.textContent') == 'Saltar al contenido'
    page.keyboard.press('Enter')
    assert page.locator('#contenido').evaluate('(node) => node === document.activeElement')
    assert not errors, errors
    for c in (context, delegate_context, other_context, admin_context):
        c.close()
    browser.close()
print('Prueba de navegador aprobada: registro, ciclo completo, aislamiento, auditoría, PC/tablet y salto por teclado.')

````


## scripts/smoke_compose.py

````
"""Verify Docker's real HTTP workflow with temporary fictional accounts.

Requires Docker Compose, Playwright and Chromium on the machine running this
optional verifier. It never reads or prints the demonstration passwords.
"""
from datetime import timedelta
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import uuid

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
BASE = os.environ.get('SMOKE_BASE_URL', 'http://127.0.0.1:8000').rstrip('/')
OUT = ROOT / '.local/browser'
OUT.mkdir(exist_ok=True)
prefix = 'qa.' + uuid.uuid4().hex[:10]
password = secrets.token_urlsafe(24)
process_env = os.environ.copy()
process_env['QA_PREFIX'] = prefix
process_env['QA_PASSWORD'] = password


def shell(code):
    return subprocess.run(['docker', 'compose', 'exec', '-T', '-e', 'QA_PREFIX', '-e', 'QA_PASSWORD',
        'web', 'python', 'manage.py', 'shell', '--no-imports', '-c', code], cwd=ROOT,
        env=process_env, check=True, capture_output=True, text=True)


setup = '''
import os
from apps.cuentas.models import Usuario
from apps.delegaciones.models import Delegacion
for suffix, role, name in [('func','funcionario','Delegación Norte (Demo)'),
                            ('del','delegado','Delegación Norte (Demo)'),
                            ('sur','funcionario','Delegación Sur (Demo)'),
                            ('admin','administrador',None)]:
    delegation = Delegacion.objects.get(nombre=name) if name else None
    user = Usuario(username=os.environ['QA_PREFIX']+'.'+suffix, rol=role, delegacion=delegation,
                   is_staff=role=='administrador', is_superuser=role=='administrador')
    user.set_password(os.environ['QA_PASSWORD'])
    user.full_clean()
    user.save()
'''
cleanup = '''
import os
from apps.cuentas.models import Usuario
from apps.agenda.models import Cita
from apps.agenda.services import cambiar_estado
prefix = os.environ['QA_PREFIX']+'.'
actor = Usuario.objects.filter(username=prefix+'admin').first()
if actor:
    for cita in Cita.objects.filter(funcionario__username__startswith=prefix, estado='programada'):
        cambiar_estado(actor, cita.pk, 'programada', 'cancelada', 'Fin de la comprobación Docker con datos ficticios')
Usuario.objects.filter(username__startswith=prefix).update(is_active=False)
'''


def login(browser, suffix):
    context = browser.new_context(viewport={'width': 1280, 'height': 900}, locale='es-CL')
    page = context.new_page()
    response = page.goto(BASE + '/acceso/')
    assert response.status == 200
    page.locator('#id_username').fill(prefix + '.' + suffix)
    page.locator('#id_password').fill(password)
    page.get_by_role('button', name='Ingresar al sistema').click()
    page.wait_for_url(BASE + '/')
    return context, page


shell(setup)
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox'])
        contexts = []
        context, page = login(browser, 'func')
        contexts.append(context)
        page.goto(BASE + '/solicitudes/nueva/')
        page.locator('#id_vecino').select_option(label='Vecina de Ejemplo · 12345678-5')
        page.locator('#id_tipo').select_option('reclamo')
        page.locator('#id_descripcion').fill('Verificación funcional de la distribución Docker con datos ficticios.')
        page.get_by_role('button', name='Guardar', exact=True).click()
        page.wait_for_url(re.compile(r'/solicitudes/\d+/$'))
        url = page.url

        context, delegate = login(browser, 'del')
        contexts.append(context)
        delegate.goto(url)
        delegate.locator('#id_responsable').select_option(label=prefix + '.func')
        delegate.locator('#id_motivo').fill('Asignación de prueba Docker')
        delegate.get_by_role('button', name='Confirmar cambio de estado').click()
        page.reload()
        for text, expected in [('Inicio de atención Docker', 'En atención'), ('Solución ficticia verificada', 'Resuelta')]:
            page.locator('#id_motivo').fill(text)
            page.get_by_role('button', name='Confirmar cambio de estado').click()
            assert page.locator('.badge').inner_text() == expected
        delegate.reload()
        delegate.locator('#id_motivo').fill('Cierre de prueba Docker')
        delegate.get_by_role('button', name='Confirmar cambio de estado').click()
        assert delegate.locator('.badge').inner_text() == 'Cerrada'
        assert delegate.locator('.timeline li').count() == 4

        page.goto(BASE + '/agenda/nueva/')
        page.locator('#id_vecino').select_option(label='Vecina de Ejemplo · 12345678-5')
        page.locator('#id_funcionario').select_option(label=prefix + '.func')
        # The browser verifier runs on the same cloud machine. Choose a date
        # from the Django application's clock without touching credentials.
        result = shell("from django.utils import timezone; from datetime import timedelta; print(timezone.localtime(timezone.now()+timedelta(days=2)).replace(hour=10, minute=0, second=0, microsecond=0).strftime('%Y-%m-%dT%H:%M'))")
        page.locator('#id_inicio').fill(result.stdout.strip())
        page.locator('#id_duracion').select_option('30')
        page.locator('#id_motivo').fill('Reserva ficticia para prueba Docker')
        page.get_by_role('button', name='Guardar', exact=True).click()
        page.wait_for_url(re.compile(r'/agenda/\d+/$'))
        cita_url = page.url
        assert page.locator('.badge').inner_text() == 'Programada'
        page.locator('#id_nuevo').select_option('cancelada')
        page.locator('#id_motivo').fill('Cancelación de prueba Docker')
        page.get_by_role('button', name='Confirmar acción').click()
        assert page.locator('.badge').inner_text() == 'Cancelada'

        delegate.goto(BASE + '/reportes/?estado=cerrada')
        assert int(delegate.locator('.report-total strong').inner_text()) >= 1
        assert page.goto(BASE + '/reportes/').status == 403
        page.goto(BASE + '/vecinos/')
        page.clock.install()
        # Force only this QA account's last-activity time into the past. The
        # private page must reject its still-existing session immediately.
        shell("from django.contrib.sessions.models import Session; from time import time; from apps.cuentas.models import Usuario; uid=str(Usuario.objects.get(username=os.environ['QA_PREFIX']+'.func').pk); "
              "sessions=[s for s in Session.objects.all() if s.get_decoded().get('_auth_user_id')==uid]; "
              "[(setattr(s, 'session_data', s.get_session_store_class()().encode(dict(s.get_decoded(), ultima_actividad=time()-1801))), s.save(update_fields=['session_data'])) for s in sessions]")
        page.clock.fast_forward(1801000)
        page.wait_for_url('**/acceso/')
        assert '/acceso/' in page.url
        assert page.locator('#id_username').count() == 1
        context, other = login(browser, 'sur')
        contexts.append(context)
        assert other.goto(url).status == 404
        assert other.goto(cita_url).status == 404
        context, admin = login(browser, 'admin')
        contexts.append(context)
        admin.goto(BASE + '/auditoria/')
        assert admin.get_by_text('cita.cancelada', exact=True).count() > 0
        for context in contexts:
            context.close()
        browser.close()
finally:
    shell(cleanup)

(OUT / 'docker.json').write_text(json.dumps({'result': 'passed', 'checks': [
    'login', 'ciclo_solicitud', 'agenda', 'cancelacion', 'reportes', 'aislamiento', 'auditoria', 'inactividad_servidor_y_navegador'],
    'test_accounts': 'disabled_after_execution'}, indent=2))
print('Distribución Docker verificada en navegador; cuentas ficticias de prueba desactivadas.')

````


## scripts/smoke_ec2.py

````
"""Verify the EC2 stack against the operator's endpoint, without AWS API access.

Run explicitly on a prepared stack. Creates synthetic requests and temporary QA
accounts, then disables the QA accounts. Default TLS verification uses public
trust roots; --ca is only for an isolated local rehearsal certificate.
"""
import argparse
import http.cookiejar
import json
import os
from pathlib import Path
import secrets
import ssl
import subprocess
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import build_opener, HTTPCookieProcessor, HTTPSHandler, Request

from ec2_config import ROOT, read_config

parser = argparse.ArgumentParser()
parser.add_argument('--ca')
arguments = parser.parse_args()
public_ip = read_config()['PUBLIC_IP']
base = os.environ.get('SMOKE_BASE_URL', 'https://' + public_ip).rstrip('/')
if not base.startswith('https://'):
    raise SystemExit('La comprobación requiere HTTPS.')
prefix = 'qa.ec2.' + secrets.token_hex(6)
env = os.environ.copy()
env['QA_PREFIX'], env['QA_PASSWORD'] = prefix, secrets.token_urlsafe(24)
context = ssl.create_default_context(cafile=arguments.ca)


def shell(code):
    return subprocess.run(['docker', 'compose', '--env-file', '.local/ec2.env', '-f',
        'compose.ec2.yaml', 'exec', '-T', '-e', 'QA_PREFIX', '-e', 'QA_PASSWORD',
        'web', 'python', 'manage.py', 'shell', '--no-imports', '-c', code],
        cwd=ROOT, env=env, check=True, capture_output=True, text=True)


def client():
    jar = http.cookiejar.CookieJar()
    opener = build_opener(HTTPSHandler(context=context), HTTPCookieProcessor(jar))
    # The local rehearsal connects to localhost while exercising the IP Host.
    opener.addheaders = [('Host', public_ip)]
    return opener, jar


def get(opener, path):
    with opener.open(Request(base + path, headers={'Host': public_ip}), timeout=10) as response:
        return response.url, response.read().decode(), response.headers


def post(opener, jar, path, data, csrf=True):
    headers = {'Referer': 'https://' + public_ip + '/', 'Host': public_ip}
    if csrf:
        headers['X-CSRFToken'] = next(cookie.value for cookie in jar if cookie.name == 'csrftoken')
    with opener.open(Request(base + path, data=urlencode(data).encode(), headers=headers), timeout=10) as response:
        return response.url, response.read().decode(), response.headers


def login(suffix):
    opener, jar = client()
    get(opener, '/acceso/')
    url, _, _ = post(opener, jar, '/acceso/', {'username': prefix + '.' + suffix, 'password': env['QA_PASSWORD']})
    assert url.rstrip('/') == base
    session = next(cookie for cookie in jar if cookie.name == 'sessionid')
    assert session.secure and session.has_nonstandard_attr('HttpOnly')
    return opener, jar


setup = '''
import os, json
from apps.cuentas.models import Usuario
from apps.delegaciones.models import Delegacion
from apps.vecinos.models import Vecino
from django.db import connection
from pathlib import Path
with connection.cursor() as cursor:
    cursor.execute('SELECT rolsuper, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname=current_user')
    assert not any(cursor.fetchone())
assert not Path('/run/db-admin/password.txt').exists()
ids={}
for suffix, role, name in [('func','funcionario','Delegación Norte (Demo)'),
                          ('del','delegado','Delegación Norte (Demo)'),
                          ('sur','funcionario','Delegación Sur (Demo)'),
                          ('admin','administrador',None)]:
    delegation=Delegacion.objects.get(nombre=name) if name else None
    user=Usuario(username=os.environ['QA_PREFIX']+'.'+suffix,rol=role,delegacion=delegation,
                 is_staff=role=='administrador',is_superuser=role=='administrador')
    user.set_password(os.environ['QA_PASSWORD']); user.full_clean(); user.save()
    ids[suffix]=user.pk
ids['vecino']=Vecino.objects.get(rut='12345678-5',delegacion__nombre='Delegación Norte (Demo)').pk
print(json.dumps(ids))
'''
cleanup = '''
import os
from apps.cuentas.models import Usuario
Usuario.objects.filter(username__startswith=os.environ['QA_PREFIX']+'.').update(is_active=False)
'''
ids = json.loads(shell(setup).stdout)
try:
    funcionario, employee_jar = login('func')
    delegado, delegate_jar = login('del')
    _, login_page, headers = get(funcionario, '/')
    assert headers['X-Content-Type-Options'] == 'nosniff'
    assert headers['Strict-Transport-Security']
    assert headers['Cache-Control'].find('no-store') >= 0
    for asset in ('app.css', 'sesion.js'):
        get(funcionario, '/static/' + asset)
    url, page, _ = post(funcionario, employee_jar, '/solicitudes/nueva/', {
        'vecino': ids['vecino'], 'tipo': 'reclamo', 'descripcion': '<script>alert(1)</script>'})
    path = url.removeprefix(base)
    assert path.startswith('/solicitudes/') and '&lt;script&gt;alert(1)&lt;/script&gt;' in page
    for opener, jar, previous, following in [
        (delegado, delegate_jar, 'ingresada', 'asignada'),
        (funcionario, employee_jar, 'asignada', 'atencion'),
        (funcionario, employee_jar, 'atencion', 'resuelta'),
        (delegado, delegate_jar, 'resuelta', 'cerrada')]:
        _, page, _ = post(opener, jar, path + 'estado/', {
            'esperado': previous, 'nuevo': following, 'responsable': ids['func'],
            'motivo': 'Prueba ficticia del despliegue EC2: ' + following})
    assert 'Cerrada' in page
    _, report, _ = get(delegado, '/reportes/?estado=cerrada')
    assert 'report-total' in report
    for opener, forbidden, expected in [(funcionario, '/reportes/', 403),
                                         (funcionario, '/auditoria/', 403),
                                         (login('sur')[0], path, 404)]:
        try:
            get(opener, forbidden)
            raise AssertionError('Acceso no autorizado permitido')
        except HTTPError as error:
            assert error.code == expected
    try:
        post(funcionario, employee_jar, '/sesion/actividad/', {}, csrf=False)
        raise AssertionError('CSRF ausente no fue rechazado')
    except HTTPError as error:
        assert error.code == 403
    admin, _ = login('admin')
    assert 'solicitud.cerrada' in get(admin, '/auditoria/')[1]
finally:
    shell(cleanup)
out = ROOT / '.local/ec2-smoke.json'
out.write_text(json.dumps({'resultado': 'OK', 'verificacion_tls': 'CA local de ensayo' if arguments.ca else 'confianza pública',
    'comprobaciones': ['gunicorn_nginx', 'login_https', 'cookies_seguras', 'csrf', 'xss',
                      'ciclo_solicitud', 'reportes', 'aislamiento', 'auditoria', 'estaticos',
                      'db_sin_superusuario', 'web_sin_secreto_admin'],
    'cuentas_qa': 'desactivadas'}, ensure_ascii=False, indent=2) + '\n')
print('Stack EC2 verificado; TLS validado y cuentas ficticias de prueba desactivadas.')

````


## scripts/smoke_https.py

````
"""Exercise local TLS with certificate validation and ephemeral fictional login."""
import http.cookiejar
import os
from pathlib import Path
import re
import secrets
import ssl
import subprocess
import sys
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import build_opener, HTTPCookieProcessor, HTTPSHandler, Request

root = Path(__file__).resolve().parent.parent
base = os.environ.get('SMOKE_BASE_URL', 'https://localhost:8000')
env = os.environ.copy()
env['QA_TLS_USER'] = 'qa.tls.' + secrets.token_hex(6)
env['QA_TLS_PASSWORD'] = secrets.token_urlsafe(24)


def shell(code):
    return subprocess.run(['docker', 'compose', 'exec', '-T', '-e', 'QA_TLS_USER',
        '-e', 'QA_TLS_PASSWORD', 'web', 'python', 'manage.py', 'shell', '--no-imports',
        '-c', code], cwd=root, env=env, check=True, capture_output=True, text=True)


context = ssl.create_default_context(cafile=sys.argv[1])
jar = http.cookiejar.CookieJar()
client = build_opener(HTTPSHandler(context=context), HTTPCookieProcessor(jar))
shell("import os; from apps.cuentas.models import Usuario; from apps.delegaciones.models import Delegacion; "
      "u=Usuario(username=os.environ['QA_TLS_USER'],delegacion=Delegacion.objects.get(nombre='Delegación Norte (Demo)')); "
      "u.set_password(os.environ['QA_TLS_PASSWORD']); u.full_clean(); u.save()")
try:
    with client.open(base + '/acceso/', timeout=5) as response:
        token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', response.read().decode())[1]
    login = Request(base + '/acceso/', data=urlencode({'username': env['QA_TLS_USER'],
        'password': env['QA_TLS_PASSWORD'], 'csrfmiddlewaretoken': token}).encode(),
        headers={'Referer': base + '/acceso/'})
    with client.open(login, timeout=5) as response:
        assert response.url.rstrip('/') == base.rstrip('/')
        assert b'Delegaciones Municipales' in response.read()
        assert response.headers['X-Content-Type-Options'] == 'nosniff'
        assert response.headers['Strict-Transport-Security']
    session = next(cookie for cookie in jar if cookie.name == 'sessionid')
    assert session.secure and session.has_nonstandard_attr('HttpOnly')
    with client.open(base + '/static/app.css', timeout=5) as response:
        assert response.status == 200
    with client.open(base + '/static/sesion.js', timeout=5) as response:
        assert response.status == 200
    try:
        client.open(Request(base + '/sesion/actividad/', data=b'',
                            headers={'Referer': base + '/'}), timeout=5)
        raise AssertionError('CSRF no rechazó una petición sin token')
    except HTTPError as error:
        assert error.code == 403
    token = next(cookie.value for cookie in jar if cookie.name == 'csrftoken')
    with client.open(Request(base + '/sesion/actividad/', data=b'',
            headers={'Referer': base + '/', 'X-CSRFToken': token}), timeout=5) as response:
        assert response.status == 200 and b'"activa": true' in response.read()
    shell("import os; from django.contrib.sessions.models import Session; from apps.cuentas.models import Usuario; from time import time; "
          "uid=str(Usuario.objects.get(username=os.environ['QA_TLS_USER']).pk); "
          "sessions=[s for s in Session.objects.all() if s.get_decoded().get('_auth_user_id')==uid]; "
          "[(setattr(s,'session_data',s.get_session_store_class()().encode(dict(s.get_decoded(),ultima_actividad=time()-1801))),s.save(update_fields=['session_data'])) for s in sessions]")
    with client.open(base + '/vecinos/', timeout=5) as response:
        assert '/acceso/' in response.url
        assert b'id_username' in response.read()
finally:
    shell("import os; from apps.cuentas.models import Usuario; Usuario.objects.filter(username=os.environ['QA_TLS_USER']).update(is_active=False)")
print('HTTPS verificado: certificado confiable, login, cookies seguras, estáticos, CSRF e inactividad. Cuenta QA desactivada.')

````


## scripts/smoke_sprint_2.py

````
"""Functional browser check for appointments and reports using fictional data."""
import json
import os
from pathlib import Path
import re
import sys
from datetime import timedelta

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.utils import timezone
from apps.agenda.models import Cita
from apps.cuentas.models import Usuario
from apps.solicitudes.models import Solicitud

credentials = json.loads((ROOT / '.local/demo-credentials.json').read_text())
OUT = ROOT / '.local/browser'
OUT.mkdir(exist_ok=True)
BASE = 'http://127.0.0.1:8000'
employee = Usuario.objects.get(username='funcionario.norte')
start = timezone.localtime(timezone.now() + timedelta(days=3)).replace(hour=10, minute=0, second=0, microsecond=0)
while Cita.objects.filter(funcionario=employee, estado='programada', inicio__lt=start + timedelta(minutes=30), fin__gt=start).exists():
    start += timedelta(minutes=30)
expected = employee.scope(Solicitud.objects.all()).count()
expected_closed = employee.scope(Solicitud.objects.filter(estado='cerrada')).count()


def login(browser, username, width=1440):
    context = browser.new_context(viewport={'width': width, 'height': 1024})
    page = context.new_page()
    page.goto(BASE + '/acceso/')
    page.locator('#id_username').fill(username)
    page.locator('#id_password').fill(credentials[username])
    page.get_by_role('button', name='Ingresar al sistema').click()
    page.wait_for_url(BASE + '/')
    return context, page


def fill_reserva(page):
    page.goto(BASE + '/agenda/nueva/')
    page.locator('#id_vecino').select_option(label='Vecina de Ejemplo · 12345678-5')
    page.locator('#id_funcionario').select_option(label='funcionario.norte')
    page.locator('#id_inicio').fill(start.strftime('%Y-%m-%dT%H:%M'))
    page.locator('#id_duracion').select_option('30')
    page.locator('#id_motivo').fill('Atención ficticia: orientación sobre solicitud municipal.')


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
    context, page = login(browser, 'funcionario.norte')
    fill_reserva(page)
    page.get_by_role('button', name='Guardar', exact=True).click()
    page.wait_for_url(re.compile(r'/agenda/\d+/$'))
    url = page.url
    assert page.locator('.badge').inner_text() == 'Programada'
    fill_reserva(page)
    page.get_by_role('button', name='Guardar', exact=True).click()
    assert page.locator('.errorlist').inner_text().find('ya tiene una atención') >= 0
    assert page.locator('#id_motivo').input_value().startswith('Atención ficticia')
    page.goto(BASE + '/agenda/')
    page.locator('#id_fecha').fill(start.date().isoformat())
    page.get_by_role('button', name='Filtrar agenda').click()
    assert page.get_by_role('link', name=re.compile('Ver atención')).count() > 0
    page.screenshot(path=str(OUT / 'agenda-pc.png'), full_page=True)
    page.goto(url)
    page.locator('#id_nuevo').select_option('cancelada')
    page.locator('#id_motivo').fill('Cancelación ficticia para verificar liberación del horario.')
    page.get_by_role('button', name='Confirmar acción').click()
    assert page.locator('.badge').inner_text() == 'Cancelada'
    assert page.locator('.timeline li').count() == 1
    fill_reserva(page)
    page.get_by_role('button', name='Guardar', exact=True).click()
    page.wait_for_url(re.compile(r'/agenda/\d+/$'))
    new_url = page.url
    assert new_url != url
    assert page.locator('.badge').inner_text() == 'Programada'
    response = page.goto(BASE + '/reportes/')
    assert response.status == 403

    other_context, other = login(browser, 'funcionario.sur')
    response = other.goto(new_url)
    assert response.status == 404

    delegate_context, delegate = login(browser, 'delegado.norte', width=768)
    delegate.goto(new_url)
    assert delegate.locator('.badge').inner_text() == 'Programada'
    assert delegate.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    delegate.screenshot(path=str(OUT / 'atencion-tablet.png'), full_page=True)
    delegate.goto(BASE + '/reportes/')
    assert int(delegate.locator('.report-total strong').inner_text()) == expected
    delegate.locator('#id_estado').select_option('cerrada')
    delegate.get_by_role('button', name='Consultar reporte').click()
    assert int(delegate.locator('.report-total strong').inner_text()) == expected_closed
    assert delegate.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    delegate.screenshot(path=str(OUT / 'reportes-tablet.png'), full_page=True)
    delegate.locator('#id_desde').fill('2026-10-10')
    delegate.locator('#id_hasta').fill('2026-10-01')
    delegate.get_by_role('button', name='Consultar reporte').click()
    assert delegate.locator('.errorlist').count() > 0
    assert int(delegate.locator('.report-total strong').inner_text()) == 0

    admin_context, admin = login(browser, 'admin.demo')
    admin.goto(BASE + '/reportes/')
    assert admin.locator('#id_delegacion option').count() >= 3
    admin.screenshot(path=str(OUT / 'reportes-pc.png'), full_page=True)
    admin.goto(BASE + '/auditoria/')
    assert admin.get_by_text('cita.reservada', exact=True).count() > 0
    assert admin.get_by_text('cita.cancelada', exact=True).count() > 0

    (OUT / 'sprint-2.json').write_text(json.dumps({'result': 'passed', 'cita_programada': int(new_url.rstrip('/').split('/')[-1]),
        'checks': ['reserva', 'conflicto', 'cancelacion', 'liberacion_horario', 'permisos', 'reportes', 'auditoria', 'pc_tablet']}, indent=2))
    for c in (context, other_context, delegate_context, admin_context):
        c.close()
    browser.close()
print('Navegador aprobado: agenda, rechazo de superposición, cancelación, aislamiento, reportes, auditoría y PC/tablet.')

````


## scripts/start.sh

````
#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
.venv/bin/python scripts/prepare.py
.venv/bin/python manage.py migrate --noinput
.venv/bin/python scripts/demo.py
exec .venv/bin/python manage.py runserver 127.0.0.1:8000 --noreload

````


## scripts/start_container.sh

````
#!/bin/sh
set -eu
cd /app
python manage.py migrate --noinput
python scripts/demo.py
python manage.py check
exec python manage.py runserver 0.0.0.0:8000 --noreload

````


## scripts/start_ec2.sh

````
#!/bin/sh
set -eu
cd /app
python manage.py migrate --noinput
if [ "${SEED_DEMO:-false}" = "true" ]; then
  python scripts/demo.py
fi
python manage.py collectstatic --noinput
python manage.py check --deploy --fail-level WARNING
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 \
  --workers 2 --threads 2 --timeout 30 --access-logfile - --error-logfile - \
  --forwarded-allow-ips ''

````


## scripts/start_https.sh

````
#!/bin/sh
set -eu
cd /app
python scripts/certificado_local.py
python manage.py migrate --noinput
python scripts/demo.py
python manage.py check --deploy
exec python scripts/serve_https.py

````


## static/app.css

````
:root{--ink:#163044;--muted:#4c6374;--teal:#116459;--line:#d4dfe5;--surface:#fff;--background:#f3f6f8}*{box-sizing:border-box}body{margin:0;color:var(--ink);background:var(--background);font:16px/1.55 system-ui,sans-serif}a{color:#075e79;text-underline-offset:3px}header{background:var(--surface);padding:24px 5%;display:flex;align-items:center;justify-content:space-between;gap:24px;border-bottom:1px solid var(--line)}.brand,.account{display:flex;gap:16px;align-items:center}.brand strong{font-size:20px}.emblem{display:grid;place-items:center;background:var(--teal);color:#fff;border-radius:12px;width:52px;height:52px;font-weight:800}small{display:block;color:var(--muted)}nav{display:flex;gap:8px;padding:10px 5%;background:#173c4c;flex-wrap:wrap}nav a{color:white;text-decoration:none;padding:10px 16px;border-radius:6px}nav a:hover{background:#285b6c}main{max-width:1200px;margin:36px auto;padding:0 24px;min-height:65vh}h1{font-size:clamp(25px,3.2vw,36px);line-height:1.2;margin:8px 0 18px}h2{font-size:21px;margin-top:0}.eyebrow{font-size:12px;font-weight:800;letter-spacing:1.5px;color:var(--teal);margin-bottom:8px}.lead{color:var(--muted);max-width:720px}.card{background:white;border:1px solid var(--line);border-radius:14px;padding:26px;margin-bottom:22px;box-shadow:0 4px 18px #12354405}.stats{display:grid;grid-template-columns:1fr 1fr 1.4fr;gap:20px;margin-top:28px}.stats strong{display:block;font-size:42px;color:var(--teal)}.stats span{color:var(--muted)}.stats h2{margin-top:16px}.actions,.heading,.filters{display:flex;gap:14px;align-items:center;flex-wrap:wrap}.actions{margin:0 0 28px}.heading{justify-content:space-between;margin-bottom:20px}button,.button{font:inherit;font-weight:650;cursor:pointer;border:1px solid var(--teal);background:var(--teal);color:white;padding:11px 18px;border-radius:7px;text-decoration:none;display:inline-block;min-height:44px}button:hover,.button:hover{background:#0a4b43}.secondary{background:white;color:var(--teal)}.secondary:hover{background:#e9f5f1;color:#10483f}input,select,textarea{font:inherit;border:1px solid #8ca1af;border-radius:6px;padding:11px;color:var(--ink);background:white;max-width:100%;width:100%;min-height:44px}textarea{min-height:110px;resize:vertical}input:disabled,select:disabled{background:#edf2f5}label{font-weight:650;display:block;margin-bottom:5px}.field{margin:20px 0}.hint{color:var(--muted);font-size:14px}.filters{margin-bottom:20px}.filters input,.filters select{width:260px}.filters label{margin:0}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse;text-align:left}th{font-size:13px;color:var(--muted);background:#f7f9fa}th,td{padding:15px 12px;border-bottom:1px solid var(--line);vertical-align:top}td a{font-weight:650}.badge{font-size:13px;font-weight:700;padding:5px 10px;background:#edf2f7;color:#294356;border-radius:20px;white-space:nowrap}.atencion,.asignada{background:#e5f0fa;color:#154e7d}.resuelta,.cerrada{background:#e2f4ea;color:#1b5d3c}.detail-grid{display:grid;grid-template-columns:1fr 1fr;gap:22px}.folio{overflow-wrap:anywhere}dt{font-size:13px;font-weight:700;color:var(--muted);margin-top:16px}dd{margin:3px 0}.timeline{padding-left:24px}.timeline li{padding:0 0 20px 10px}.note{border-bottom:1px solid var(--line);padding:14px 0}.login{max-width:480px;margin:60px auto}.form-card{max-width:720px;margin:auto}.errorlist{padding:12px 24px;border-left:4px solid #ac2525;background:#fff0f0;color:#8b1e1e}.message{padding:14px 18px;background:#e5f2ee;border:1px solid #98c7b5;border-radius:8px;margin-bottom:18px}.message.error{background:#fff0f0;border-color:#d79c9c;color:#8b1e1e}.pagination{display:flex;gap:20px;padding-top:18px;flex-wrap:wrap}footer{padding:24px;text-align:center;font-size:13px;color:var(--muted)}:focus-visible{outline:3px solid #b25700;outline-offset:3px}.skip{position:absolute;top:-100px;background:white;padding:15px;z-index:10}.skip:focus{top:0}.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0)}@media(max-width:800px){header{align-items:flex-start;flex-direction:column;padding:20px}.stats,.detail-grid{grid-template-columns:1fr}.stats{gap:0}main{margin:24px auto;padding:0 16px}.card{padding:20px}.account{width:100%;justify-content:space-between}nav{padding:8px}.heading{align-items:flex-start}.filters{align-items:stretch;flex-direction:column}.filters input,.filters select{width:100%}.login{margin-top:20px}th,td{padding:12px}.brand strong{font-size:18px}}
.filter-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:18px;margin-bottom:24px;align-items:start}.filter-grid>.errorlist{grid-column:1/-1}.filter-actions{display:flex;gap:16px;align-items:center;flex-wrap:wrap;align-self:end}.report-total{display:flex;align-items:center;justify-content:space-between;gap:20px}.report-total strong{font-size:40px;color:var(--teal)}.programada{background:#e5f0fa;color:#154e7d}.atendida{background:#e2f4ea;color:#1b5d3c}.cancelada{background:#fbeaea;color:#8b2929}@media(max-width:500px){.filter-grid{grid-template-columns:1fr}}

````


## static/sesion.js

````
// Report actual interaction; an unattended page never renews its session.
(() => {
  const limit = 30 * 60 * 1000;
  let lastActivity = Date.now();
  let lastSent = 0;
  let pending = false;
  const expired = () => window.location.replace('/acceso/');
  async function interaction() {
    if (Date.now() - lastActivity >= limit) return expired();
    lastActivity = Date.now();
    if (pending || Date.now() - lastSent < 10000) return;
    const token = document.querySelector('[name=csrfmiddlewaretoken]');
    if (!token) return;
    pending = true;
    lastSent = Date.now();
    try {
      const response = await fetch('/sesion/actividad/', {
        method: 'POST', credentials: 'same-origin',
        headers: {'X-CSRFToken': token.value}
      });
      if (response.redirected) expired();
    } catch (_) {
      // The server remains authoritative when a connection is interrupted.
    } finally { pending = false; }
  }
  ['pointerdown', 'keydown', 'input', 'scroll'].forEach(name =>
    document.addEventListener(name, interaction, {passive: true}));
  setInterval(() => {
    if (Date.now() - lastActivity >= limit) expired();
  }, 1000);
})();

````


## templates/403.html

````
{% extends 'base.html' %}{% block content %}<section class="card"><h1>Acceso denegado</h1><p>Tu cuenta no tiene permisos para realizar esta acción.</p><a href="{% url 'inicio' %}">Volver al inicio</a></section>{% endblock %}

````


## templates/404.html

````
{% extends 'base.html' %}{% block content %}<section class="card"><h1>Registro no disponible</h1><p>El registro no existe o no está disponible para tu cuenta.</p><a href="{% url 'inicio' %}">Volver al inicio</a></section>{% endblock %}

````


## templates/500.html

````
{% extends 'base.html' %}{% block content %}<section class="card"><h1>No se pudo completar la operación</h1><p>Se produjo un error interno. Contacta al administrador si el problema continúa.</p><a href="{% url 'inicio' %}">Volver al inicio</a></section>{% endblock %}

````


## templates/agenda.html

````
{% extends 'base.html' %}
{% block title %}Agenda · Delegaciones Municipales{% endblock %}
{% block content %}
<div class="heading"><div><p class="eyebrow">ATENCIÓN DE PÚBLICO</p><h1>Agenda de atenciones</h1></div><a class="button" href="{% url 'cita_crear' %}">Reservar atención</a></div>
<p class="lead">Consulta las reservas de tu delegación. Las horas se muestran en el horario de Chile.</p>
<section class="card">
<form method="get" class="filter-grid">{{ filtros.non_field_errors }}{% for field in filtros %}<div>{{ field.label_tag }}{{ field }}{{ field.errors }}</div>{% endfor %}<div class="filter-actions"><button type="submit">Filtrar agenda</button><a href="{% url 'agenda' %}">Limpiar filtros</a></div></form>
<div class="table-wrap" role="region" aria-label="Atenciones agendadas" tabindex="0"><table><caption class="sr-only">Agenda de las delegaciones autorizadas</caption><thead><tr><th scope="col">Fecha y hora</th><th scope="col">Vecino</th><th scope="col">Funcionario</th><th scope="col">Delegación</th><th scope="col">Estado</th><th scope="col">Acción</th></tr></thead><tbody>
{% for cita in pagina %}<tr><td>{{ cita.inicio|date:'d/m/Y' }}<small>{{ cita.inicio|date:'H:i' }}–{{ cita.fin|date:'H:i' }}</small></td><td>{{ cita.vecino.nombre }}</td><td>{{ cita.funcionario.get_full_name|default:cita.funcionario.username }}</td><td>{{ cita.delegacion }}</td><td><span class="badge {{ cita.estado }}">{{ cita.get_estado_display }}</span></td><td><a href="{% url 'cita_detalle' cita.pk %}" aria-label="Ver atención de {{ cita.vecino.nombre }} del {{ cita.inicio|date:'d/m/Y H:i' }}">Ver atención</a></td></tr>{% empty %}<tr><td colspan="6">No hay atenciones para los filtros seleccionados.</td></tr>{% endfor %}
</tbody></table></div>{% include 'paginacion_filtros.html' %}
</section>{% endblock %}

````


## templates/auditoria.html

````
{% extends 'base.html' %}{% block content %}<h1>Auditoría</h1><p>Registro de acciones del prototipo. Consulta reservada al administrador.</p><section class="card"><div class="table-wrap" role="region" aria-label="Eventos de auditoría" tabindex="0"><table><thead><tr><th>Fecha</th><th>Actor</th><th>Acción</th><th>Entidad</th><th>Identificador</th></tr></thead><tbody>{% for evento in pagina %}<tr><td>{{ evento.fecha|date:'d/m/Y H:i:s' }}</td><td>{{ evento.actor.username|default:'Sistema' }}</td><td>{{ evento.accion }}</td><td>{{ evento.entidad }}</td><td>{{ evento.objeto_id }}</td></tr>{% empty %}<tr><td colspan="5">Sin eventos.</td></tr>{% endfor %}</tbody></table></div>{% include 'paginacion.html' %}</section>{% endblock %}

````


## templates/base.html

````
{% load static %}
<!doctype html>
<html lang="es">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{% block title %}Delegaciones Municipales{% endblock %}</title><link rel="stylesheet" href="{% static 'app.css' %}"></head>
<body>
<a class="skip" href="#contenido">Saltar al contenido</a>
<header><div class="brand"><span class="emblem" aria-hidden="true">DM</span><div><strong>Delegaciones Municipales</strong><small>Gestión y atención ciudadana · Prototipo</small></div></div>
{% if user.is_authenticated %}<div class="account"><span>{{ user.get_full_name|default:user.username }}<small>{{ user.get_rol_display }} · {{ user.delegacion|default:'Todas las delegaciones' }}</small></span><form method="post" action="{% url 'logout' %}">{% csrf_token %}<button class="secondary" type="submit">Salir</button></form></div>{% endif %}</header>
{% if user.is_authenticated %}<nav aria-label="Navegación principal"><a href="{% url 'inicio' %}">Inicio</a><a href="{% url 'vecinos' %}">Vecinos</a><a href="{% url 'solicitudes' %}">Solicitudes</a><a href="{% url 'agenda' %}">Agenda</a>{% if user.supervisa %}<a href="{% url 'reportes' %}">Reportes</a>{% endif %}{% if user.administra %}<a href="{% url 'auditoria' %}">Auditoría</a><a href="/admin/">Administración</a>{% endif %}</nav>{% endif %}
<main id="contenido" tabindex="-1">{% for message in messages %}<div class="message {{ message.tags }}" role="status">{{ message }}</div>{% endfor %}{% block content %}{% endblock %}</main>
<footer>Demostración académica · Solo datos ficticios · Horario de Chile</footer>
{% if user.is_authenticated %}<script src="{% static 'sesion.js' %}" defer></script>{% endif %}
</body></html>

````


## templates/cita_detalle.html

````
{% extends 'base.html' %}
{% block title %}Atención #{{ cita.pk }} · Delegaciones Municipales{% endblock %}
{% block content %}
<a href="{% url 'agenda' %}">← Volver a la agenda</a>
<div class="heading"><div><p class="eyebrow">{{ cita.delegacion }}</p><h1>Atención #{{ cita.pk }}</h1></div><span class="badge {{ cita.estado }}">{{ cita.get_estado_display }}</span></div>
<div class="detail-grid"><section class="card"><h2>Datos de la reserva</h2><dl><dt>Vecino</dt><dd>{{ cita.vecino }}</dd><dt>Funcionario</dt><dd>{{ cita.funcionario.get_full_name|default:cita.funcionario.username }}</dd><dt>Fecha y hora (Chile)</dt><dd>{{ cita.inicio|date:'d/m/Y H:i' }} a {{ cita.fin|date:'H:i' }}</dd><dt>Motivo</dt><dd>{{ cita.motivo|linebreaksbr }}</dd>{% if cita.solicitud %}<dt>Solicitud relacionada</dt><dd><a href="{% url 'solicitud_detalle' cita.solicitud.pk %}">Solicitud #{{ cita.solicitud.pk }}</a></dd>{% endif %}</dl></section>
<section class="card"><h2>Gestionar atención</h2>{% if form %}<p>Para cambiar el horario, cancela esta reserva y crea una nueva. Solo el funcionario de atención o un supervisor pueden marcarla como atendida.</p><form method="post" action="{% url 'cita_estado' cita.pk %}">{% csrf_token %}{{ form.as_p }}<button type="submit">Confirmar acción</button></form>{% else %}<p>Esta atención ya finalizó. Su historial se conserva.</p>{% endif %}</section></div>
<section class="card"><h2>Historial de la atención</h2><ol class="timeline">{% for cambio in cambios %}<li><strong>{{ cambio.get_anterior_display }} → {{ cambio.get_nuevo_display }}</strong><small>{{ cambio.fecha|date:'d/m/Y H:i' }} · {{ cambio.actor.username }}</small><p>{{ cambio.motivo|linebreaksbr }}</p></li>{% empty %}<li>Reserva creada. No se han registrado cambios de estado.</li>{% endfor %}</ol></section>
{% endblock %}

````


## templates/detalle.html

````
{% extends 'base.html' %}{% block content %}<a href="{% url 'solicitudes' %}">← Volver a solicitudes</a><div class="heading"><div><p class="eyebrow">{{ solicitud.delegacion }}</p><h1>Solicitud #{{ solicitud.pk }} · {{ solicitud.get_tipo_display }}</h1></div><span class="badge {{ solicitud.estado }}">{{ solicitud.get_estado_display }}</span></div><div class="detail-grid"><section class="card"><h2>Datos de la solicitud</h2><dl><dt>Folio</dt><dd class="folio">{{ solicitud.folio }}</dd><dt>Vecino</dt><dd>{{ solicitud.vecino }}</dd><dt>Responsable</dt><dd>{% if solicitud.responsable %}{{ solicitud.responsable.get_full_name|default:solicitud.responsable.username }}{% else %}Pendiente de asignación{% endif %}</dd><dt>Ingreso</dt><dd>{{ solicitud.creada_en|date:'d/m/Y H:i' }}</dd><dt>Descripción</dt><dd>{{ solicitud.descripcion|linebreaksbr }}</dd></dl></section>{% if transicion %}<section class="card"><h2>Avanzar a: {{ accion }}</h2><form method="post" action="{% url 'solicitud_transicion' solicitud.pk %}">{% csrf_token %}{{ transicion.as_p }}<button type="submit">Confirmar cambio de estado</button></form></section>{% else %}<section class="card"><h2>Seguimiento</h2><p>{% if solicitud.estado == 'cerrada' %}Esta solicitud finalizó su atención.{% else %}El siguiente paso corresponde al responsable o al delegado autorizado.{% endif %}</p></section>{% endif %}</div><section class="card"><h2>Historial de estados</h2><ol class="timeline">{% for cambio in cambios %}<li><strong>{{ cambio.get_anterior_display }} → {{ cambio.get_nuevo_display }}</strong><small>{{ cambio.fecha|date:'d/m/Y H:i' }} · {{ cambio.actor.username }}</small><p>{{ cambio.motivo|linebreaksbr }}</p></li>{% empty %}<li>Solicitud ingresada. Aún no hay cambios de estado.</li>{% endfor %}</ol></section><section class="card"><h2>Observaciones</h2>{% for o in observaciones %}<article class="note"><small>{{ o.fecha|date:'d/m/Y H:i' }} · {{ o.autor.username }}</small><p>{{ o.texto|linebreaksbr }}</p></article>{% empty %}<p>No hay observaciones registradas.</p>{% endfor %}{% if solicitud.estado != 'cerrada' %}<form method="post" action="{% url 'solicitud_observacion' solicitud.pk %}">{% csrf_token %}{{ observacion.as_p }}<button type="submit">Agregar observación</button></form>{% endif %}</section>{% endblock %}

````


## templates/form.html

````
{% extends 'base.html' %}{% block content %}<section class="card form-card"><h1>{{ titulo }}</h1><p>Completa los campos indicados. Los campos sin la marca «opcional» son obligatorios.</p><form method="post">{% csrf_token %}{{ form.non_field_errors }}{% for field in form %}<div class="field">{{ field.label_tag }}{% if not field.field.required %}<span class="hint"> (opcional)</span>{% endif %}{{ field }}{% if field.help_text %}<small>{{ field.help_text }}</small>{% endif %}{{ field.errors }}</div>{% endfor %}<button type="submit">Guardar</button></form></section>{% endblock %}

````


## templates/inicio.html

````
{% extends 'base.html' %}{% block content %}<p class="eyebrow">PANEL DE ATENCIÓN</p><h1>Una atención más cercana</h1><p class="lead">Registra vecinos y acompaña cada solicitud desde su ingreso hasta su cierre.</p><div class="stats"><section class="card"><span>Solicitudes registradas</span><strong>{{ total }}</strong></section><section class="card"><span>Pendientes de cierre</span><strong>{{ pendientes }}</strong></section><section class="card"><span>Tu ámbito de trabajo</span><h2>{{ user.delegacion|default:'Todas las delegaciones' }}</h2></section></div><div class="actions"><a class="button" href="{% url 'solicitud_crear' %}">Ingresar solicitud</a><a class="button secondary" href="{% url 'vecino_crear' %}">Registrar vecino</a></div><section class="card"><h2>Últimas solicitudes</h2>{% include 'tabla_solicitudes.html' with filas=solicitudes %}</section>{% endblock %}

````


## templates/paginacion.html

````
{% if pagina.has_other_pages %}<div class="pagination" aria-label="Paginación">{% if pagina.has_previous %}<a href="?page={{ pagina.previous_page_number }}&amp;q={{ q|urlencode }}&amp;estado={{ estado|urlencode }}">Anterior</a>{% endif %}<span>Página {{ pagina.number }} de {{ pagina.paginator.num_pages }}</span>{% if pagina.has_next %}<a href="?page={{ pagina.next_page_number }}&amp;q={{ q|urlencode }}&amp;estado={{ estado|urlencode }}">Siguiente</a>{% endif %}</div>{% endif %}

````


## templates/paginacion_filtros.html

````
{% if pagina.has_other_pages %}<div class="pagination" aria-label="Paginación">{% if pagina.has_previous %}<a href="?{{ filtros_query }}&amp;page={{ pagina.previous_page_number }}">Anterior</a>{% endif %}<span>Página {{ pagina.number }} de {{ pagina.paginator.num_pages }}</span>{% if pagina.has_next %}<a href="?{{ filtros_query }}&amp;page={{ pagina.next_page_number }}">Siguiente</a>{% endif %}</div>{% endif %}

````


## templates/registration/locked.html

````
{% extends 'base.html' %}{% block content %}<section class="card"><h1>Acceso temporalmente limitado</h1><p>Se registraron varios intentos fallidos. Vuelve a intentarlo después de una hora o contacta al administrador.</p></section>{% endblock %}

````


## templates/registration/login.html

````
{% extends 'base.html' %}
{% block title %}Acceso · Delegaciones Municipales{% endblock %}
{% block content %}<section class="login card"><p class="eyebrow">ATENCIÓN MUNICIPAL</p><h1>Bienvenido</h1><p>Ingresa con tu cuenta institucional para gestionar la atención de tu delegación.</p><form method="post">{% csrf_token %}{{ form.as_p }}{% if next %}<input type="hidden" name="next" value="{{ next }}">{% endif %}<button type="submit">Ingresar al sistema</button></form><p class="hint">El acceso está reservado al personal autorizado.</p></section>{% endblock %}

````


## templates/reportes.html

````
{% extends 'base.html' %}
{% block title %}Reportes · Delegaciones Municipales{% endblock %}
{% block content %}
<p class="eyebrow">SUPERVISIÓN MUNICIPAL</p><h1>Reportes de solicitudes</h1>
<p class="lead">Consulta el estado actual de las solicitudes según su fecha de ingreso. El período incluye ambos días, en horario de Chile.</p>
<section class="card"><h2>Filtros del reporte</h2><form method="get" class="filter-grid">{{ filtros.non_field_errors }}{% for field in filtros %}<div>{{ field.label_tag }}{{ field }}{{ field.errors }}</div>{% endfor %}<div class="filter-actions"><button type="submit">Consultar reporte</button><a href="{% url 'reportes' %}">Limpiar filtros</a></div></form></section>
<section class="card report-total"><span>Solicitudes que cumplen los filtros</span><strong>{{ total }}</strong></section>
<div class="detail-grid"><section class="card"><h2>Por estado actual</h2><table><caption class="sr-only">Recuento por estado</caption><thead><tr><th scope="col">Estado</th><th scope="col">Solicitudes</th></tr></thead><tbody>{% for fila in por_estado %}<tr><th scope="row">{{ fila.nombre }}</th><td>{{ fila.total }}</td></tr>{% endfor %}</tbody></table></section><section class="card"><h2>Por delegación</h2><table><caption class="sr-only">Recuento por delegación</caption><thead><tr><th scope="col">Delegación</th><th scope="col">Solicitudes</th></tr></thead><tbody>{% for fila in por_delegacion %}<tr><th scope="row">{{ fila.delegacion__nombre }}</th><td>{{ fila.total }}</td></tr>{% empty %}<tr><td colspan="2">Sin solicitudes para este período.</td></tr>{% endfor %}</tbody></table></section></div>
<section class="card"><h2>Detalle de solicitudes</h2>{% include 'tabla_solicitudes.html' with filas=pagina %}{% include 'paginacion_filtros.html' %}</section>
{% endblock %}

````


## templates/solicitudes.html

````
{% extends 'base.html' %}{% block content %}<div class="heading"><div><p class="eyebrow">SEGUIMIENTO DE ATENCIÓN</p><h1>Solicitudes</h1></div><a class="button" href="{% url 'solicitud_crear' %}">Ingresar solicitud</a></div><section class="card"><form class="filters" method="get"><label for="estado">Estado</label><select id="estado" name="estado"><option value="">Todos</option>{% for valor, etiqueta in estados %}<option value="{{ valor }}" {% if estado == valor %}selected{% endif %}>{{ etiqueta }}</option>{% endfor %}</select><button type="submit">Filtrar</button></form>{% include 'tabla_solicitudes.html' with filas=pagina %}{% include 'paginacion.html' %}</section>{% endblock %}

````


## templates/tabla_solicitudes.html

````
<div class="table-wrap" role="region" aria-label="Solicitudes" tabindex="0"><table><caption class="sr-only">Solicitudes visibles para el usuario</caption><thead><tr><th scope="col">Solicitud</th><th scope="col">Vecino</th><th scope="col">Delegación</th><th scope="col">Estado</th><th scope="col">Fecha</th></tr></thead><tbody>{% for s in filas %}<tr><td><a href="{% url 'solicitud_detalle' s.pk %}">#{{ s.pk }} · {{ s.get_tipo_display }}</a></td><td>{{ s.vecino.nombre }}</td><td>{{ s.delegacion }}</td><td><span class="badge {{ s.estado }}">{{ s.get_estado_display }}</span></td><td>{{ s.creada_en|date:'d/m/Y H:i' }}</td></tr>{% empty %}<tr><td colspan="5">Todavía no hay solicitudes en esta vista.</td></tr>{% endfor %}</tbody></table></div>

````


## templates/vecinos.html

````
{% extends 'base.html' %}{% block content %}<div class="heading"><div><p class="eyebrow">REGISTRO CIUDADANO</p><h1>Vecinos</h1></div><a class="button" href="{% url 'vecino_crear' %}">Registrar vecino</a></div><section class="card"><form class="filters" method="get"><label for="q">Buscar por nombre o RUT</label><input id="q" name="q" value="{{ q }}" maxlength="100"><button type="submit">Buscar</button></form><div class="table-wrap" role="region" aria-label="Vecinos registrados" tabindex="0"><table><caption class="sr-only">Vecinos de las delegaciones autorizadas</caption><thead><tr><th scope="col">Nombre</th><th scope="col">RUT</th><th scope="col">Delegación</th><th scope="col">Contacto</th><th scope="col">Acción</th></tr></thead><tbody>{% for vecino in pagina %}<tr><td>{{ vecino.nombre }}</td><td>{{ vecino.rut }}</td><td>{{ vecino.delegacion }}</td><td>{{ vecino.email|default:vecino.telefono }}</td><td><a href="{% url 'vecino_editar' vecino.pk %}" aria-label="Editar a {{ vecino.nombre }}">Editar</a></td></tr>{% empty %}<tr><td colspan="5">No se encontraron vecinos. Registra el primero para ingresar una solicitud.</td></tr>{% endfor %}</tbody></table></div>{% include 'paginacion.html' %}</section>{% endblock %}

````

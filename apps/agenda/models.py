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

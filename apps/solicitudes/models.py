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

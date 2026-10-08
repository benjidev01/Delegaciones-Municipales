from django.db import models

class Evento(models.Model):
    actor = models.ForeignKey('cuentas.Usuario', on_delete=models.PROTECT, null=True)
    accion = models.CharField(max_length=80)
    entidad = models.CharField(max_length=80)
    objeto_id = models.CharField(max_length=80)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha', '-pk']

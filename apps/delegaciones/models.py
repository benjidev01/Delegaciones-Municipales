from django.db import models

class Delegacion(models.Model):
    nombre = models.CharField(max_length=120, unique=True)
    direccion = models.CharField('dirección', max_length=200)
    activa = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre

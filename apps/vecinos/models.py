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

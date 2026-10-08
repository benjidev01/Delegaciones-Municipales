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

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

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

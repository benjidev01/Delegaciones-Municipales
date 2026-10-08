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

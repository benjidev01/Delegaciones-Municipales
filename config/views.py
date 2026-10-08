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

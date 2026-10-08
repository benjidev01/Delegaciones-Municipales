from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import AgendaFiltroForm, CitaForm, CambioCitaForm
from .models import Cita
from .services import reservar, cambiar_estado


@login_required
def agenda(request):
    qs = request.user.scope(Cita.objects.select_related('vecino', 'funcionario', 'delegacion'))
    form = AgendaFiltroForm(request.GET)
    if form.is_valid():
        if form.cleaned_data['fecha']:
            qs = qs.filter(inicio__date=form.cleaned_data['fecha'])
        if form.cleaned_data['estado']:
            qs = qs.filter(estado=form.cleaned_data['estado'])
    else:
        qs = qs.none()
    query = request.GET.copy()
    query.pop('page', None)
    return render(request, 'agenda.html', {'filtros': form,
        'pagina': Paginator(qs, 20).get_page(request.GET.get('page')),
        'filtros_query': query.urlencode()})


@login_required
def cita_crear(request):
    form = CitaForm(request.POST if request.method == 'POST' else None, usuario=request.user)
    if request.method == 'POST' and form.is_valid():
        try:
            cita = reservar(request.user, **form.cleaned_data)
        except ValidationError as error:
            form.add_error(None, ' '.join(error.messages))
        else:
            messages.success(request, 'Atención reservada y registrada en auditoría.')
            return redirect('cita_detalle', pk=cita.pk)
    return render(request, 'form.html', {'form': form, 'titulo': 'Reservar atención'})


def detalle_response(request, cita, form=None, status=200):
    if form is None and cita.estado == Cita.Estado.PROGRAMADA:
        form = CambioCitaForm(usuario=request.user, cita=cita)
    return render(request, 'cita_detalle.html', {'cita': cita, 'form': form,
        'cambios': cita.cambios.select_related('actor')}, status=status)


@login_required
def cita_detalle(request, pk):
    cita = get_object_or_404(request.user.scope(Cita.objects.select_related('vecino', 'funcionario', 'delegacion', 'solicitud')), pk=pk)
    return detalle_response(request, cita)


@login_required
@require_POST
def cita_estado(request, pk):
    cita = get_object_or_404(request.user.scope(Cita.objects.all()), pk=pk)
    form = CambioCitaForm(request.POST, usuario=request.user, cita=cita)
    if form.is_valid():
        try:
            cambiar_estado(request.user, pk, **form.cleaned_data)
        except ValidationError as error:
            form.add_error(None, ' '.join(error.messages))
            return detalle_response(request, cita, form, status=409)
        messages.success(request, 'Estado de la atención actualizado.')
        return redirect('cita_detalle', pk=pk)
    return detalle_response(request, cita, form, status=400)

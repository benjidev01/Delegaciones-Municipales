from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import render

from apps.solicitudes.models import Solicitud
from .forms import ReporteForm


@login_required
def reportes(request):
    if not request.user.supervisa:
        raise PermissionDenied
    form = ReporteForm(request.GET, usuario=request.user)
    qs = request.user.scope(Solicitud.objects.select_related('vecino', 'delegacion', 'responsable'))
    if form.is_valid():
        data = form.cleaned_data
        if data['desde']:
            qs = qs.filter(creada_en__date__gte=data['desde'])
        if data['hasta']:
            qs = qs.filter(creada_en__date__lte=data['hasta'])
        if data['estado']:
            qs = qs.filter(estado=data['estado'])
        if data['delegacion']:
            qs = qs.filter(delegacion=data['delegacion'])
    else:
        # Invalid or unauthorized filters never fall back to a wider report.
        qs = qs.none()
    counts = {row['estado']: row['total'] for row in qs.order_by().values('estado').annotate(total=Count('pk'))}
    por_estado = [{'nombre': label, 'total': counts.get(value, 0)} for value, label in Solicitud.Estado.choices]
    por_delegacion = qs.order_by().values('delegacion__nombre').annotate(total=Count('pk')).order_by('delegacion__nombre')
    query = request.GET.copy()
    query.pop('page', None)
    return render(request, 'reportes.html', {'filtros': form, 'total': qs.count(), 'por_estado': por_estado,
        'por_delegacion': por_delegacion, 'pagina': Paginator(qs, 20).get_page(request.GET.get('page')),
        'filtros_query': query.urlencode()})

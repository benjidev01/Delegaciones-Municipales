from django import forms
from django.utils import timezone

from apps.cuentas.models import Usuario
from apps.solicitudes.models import Solicitud
from apps.vecinos.models import Vecino
from .models import Cita


class CitaForm(forms.Form):
    vecino = forms.ModelChoiceField(queryset=Vecino.objects.none())
    funcionario = forms.ModelChoiceField(queryset=Usuario.objects.none(), label='Funcionario de atención')
    solicitud = forms.ModelChoiceField(queryset=Solicitud.objects.none(), required=False, label='Solicitud relacionada')
    inicio = forms.DateTimeField(label='Fecha y hora de inicio (Chile)', input_formats=['%Y-%m-%dT%H:%M'],
                                 widget=forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local'}),
                                 help_text='Horario de America/Santiago. No se aceptan fechas pasadas.')
    duracion = forms.TypedChoiceField(label='Duración', coerce=int, initial=30,
                                     choices=[(n, f'{n} minutos') for n in (15, 30, 45, 60)])
    motivo = forms.CharField(label='Motivo de atención', max_length=300, strip=True, widget=forms.Textarea)

    def __init__(self, *args, usuario, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['vecino'].queryset = usuario.scope(Vecino.objects.select_related('delegacion'))
        funcionarios = Usuario.objects.filter(is_active=True, rol='funcionario', delegacion__activa=True)
        if not usuario.administra:
            funcionarios = funcionarios.filter(delegacion_id=usuario.delegacion_id)
        self.fields['funcionario'].queryset = funcionarios.order_by('username')
        self.fields['solicitud'].queryset = usuario.scope(Solicitud.objects.exclude(estado='cerrada'))
        self.fields['solicitud'].label_from_instance = lambda s: f'#{s.pk} · {s.vecino.nombre} · {s.get_tipo_display()}'

    def clean_inicio(self):
        value = self.cleaned_data['inicio']
        if value <= timezone.now():
            raise forms.ValidationError('Seleccione una fecha y hora futuras.')
        return value


class AgendaFiltroForm(forms.Form):
    fecha = forms.DateField(label='Fecha de atención', required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    estado = forms.ChoiceField(required=False, choices=[('', 'Todos los estados')] + Cita.Estado.choices)


class CambioCitaForm(forms.Form):
    esperado = forms.ChoiceField(choices=Cita.Estado.choices, widget=forms.HiddenInput,
                                 initial=Cita.Estado.PROGRAMADA)
    nuevo = forms.ChoiceField(choices=[(Cita.Estado.CANCELADA, 'Cancelar cita'),
                                     (Cita.Estado.ATENDIDA, 'Marcar atendida')], label='Acción')
    motivo = forms.CharField(label='Motivo / resultado de la atención', max_length=1000, strip=True, widget=forms.Textarea)

    def __init__(self, *args, usuario, cita, **kwargs):
        super().__init__(*args, **kwargs)
        if usuario.pk != cita.funcionario_id and not usuario.supervisa:
            self.fields['nuevo'].choices = [(Cita.Estado.CANCELADA, 'Cancelar cita')]

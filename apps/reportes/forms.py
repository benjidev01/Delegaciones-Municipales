from django import forms

from apps.delegaciones.models import Delegacion
from apps.solicitudes.models import Solicitud


class ReporteForm(forms.Form):
    desde = forms.DateField(label='Desde (fecha de ingreso)', required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    hasta = forms.DateField(label='Hasta (inclusive)', required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    estado = forms.ChoiceField(required=False, choices=[('', 'Todos los estados')] + Solicitud.Estado.choices)
    delegacion = forms.ModelChoiceField(queryset=Delegacion.objects.none(), required=False, label='Delegación')

    def __init__(self, *args, usuario, **kwargs):
        super().__init__(*args, **kwargs)
        delegaciones = Delegacion.objects.filter(activa=True)
        if not usuario.administra:
            delegaciones = delegaciones.filter(pk=usuario.delegacion_id)
        self.fields['delegacion'].queryset = delegaciones.order_by('nombre')
        self.fields['delegacion'].empty_label = 'Todas las autorizadas'

    def clean(self):
        data = super().clean()
        desde, hasta = data.get('desde'), data.get('hasta')
        if desde and hasta and hasta < desde:
            raise forms.ValidationError('La fecha final debe ser igual o posterior a la inicial.')
        return data

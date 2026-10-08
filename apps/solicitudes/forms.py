from django import forms
from apps.cuentas.models import Usuario
from apps.vecinos.models import Vecino
from .models import Solicitud

class SolicitudForm(forms.Form):
    vecino = forms.ModelChoiceField(queryset=Vecino.objects.none())
    tipo = forms.ChoiceField(choices=Solicitud.Tipo.choices)
    descripcion = forms.CharField(label='Descripción', max_length=3000, widget=forms.Textarea)

    def __init__(self, *args, usuario, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['vecino'].queryset = usuario.scope(Vecino.objects.all())

class TransicionForm(forms.Form):
    esperado = forms.ChoiceField(choices=Solicitud.Estado.choices, widget=forms.HiddenInput)
    nuevo = forms.ChoiceField(choices=Solicitud.Estado.choices, widget=forms.HiddenInput)
    responsable = forms.ModelChoiceField(queryset=Usuario.objects.none(), required=False)
    motivo = forms.CharField(label='Observación / solución', max_length=2000, strip=True, widget=forms.Textarea)

    def __init__(self, *args, solicitud, nuevo, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['esperado'].initial = solicitud.estado
        self.fields['nuevo'].initial = nuevo
        self.fields['responsable'].queryset = Usuario.objects.filter(is_active=True, delegacion=solicitud.delegacion)
        if nuevo != Solicitud.Estado.ASIGNADA:
            self.fields['responsable'].widget = forms.HiddenInput()
        else:
            self.fields['responsable'].required = True

class ObservacionForm(forms.Form):
    texto = forms.CharField(label='Observación', max_length=2000, strip=True, widget=forms.Textarea)

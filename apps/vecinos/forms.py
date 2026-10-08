from django import forms
from apps.delegaciones.models import Delegacion
from .models import Vecino, normalizar_rut

class VecinoForm(forms.ModelForm):
    class Meta:
        model = Vecino
        fields = ['delegacion', 'rut', 'nombre', 'email', 'telefono', 'direccion']

    def __init__(self, *args, usuario, **kwargs):
        super().__init__(*args, **kwargs)
        qs = Delegacion.objects.filter(activa=True)
        if not usuario.administra:
            qs = qs.filter(pk=usuario.delegacion_id)
        self.fields['delegacion'].queryset = qs
        if not usuario.administra:
            self.fields['delegacion'].initial = usuario.delegacion_id
            self.fields['delegacion'].disabled = True
        if self.instance.pk:
            self.fields['delegacion'].initial = self.instance.delegacion_id
            self.fields['delegacion'].disabled = True

    def clean_rut(self):
        return normalizar_rut(self.cleaned_data['rut'])

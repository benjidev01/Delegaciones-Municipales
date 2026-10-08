from django.contrib import admin
from django.contrib.admin import AdminSite
from django.contrib.auth.admin import UserAdmin
from django.core.exceptions import PermissionDenied
from django.contrib.admin.utils import unquote
from django.db import transaction
from apps.delegaciones.models import Delegacion
from apps.auditoria.models import Evento
from apps.solicitudes.services import auditar
from .models import Usuario

class MunicipalAdminSite(AdminSite):
    site_header = 'Administración municipal'
    site_title = 'Delegaciones Municipales'
    index_title = 'Usuarios y delegaciones'

    def has_permission(self, request):
        return request.user.is_authenticated and request.user.is_active and request.user.administra and request.user.is_staff

municipal_site = MunicipalAdminSite(name='admin')

class ConservacionAdmin(admin.ModelAdmin):
    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        auditar(request.user, 'administracion.editado' if change else 'administracion.creado', obj)

class UsuarioAdmin(ConservacionAdmin, UserAdmin):
    fieldsets = UserAdmin.fieldsets + (('Ámbito municipal', {'fields': ('rol', 'delegacion')}),)
    add_fieldsets = UserAdmin.add_fieldsets + (('Ámbito municipal', {'fields': ('rol', 'delegacion')}),)
    list_display = ['username', 'rol', 'delegacion', 'is_active']
    list_filter = ['rol', 'delegacion', 'is_active']
    actions = None

    @transaction.atomic
    def user_change_password(self, request, id, form_url=''):
        response = super().user_change_password(request, id, form_url)
        if request.method == 'POST' and response.status_code == 302:
            usuario = self.get_object(request, unquote(id))
            auditar(request.user, 'usuario.password_cambiada', usuario)
        return response

    def save_model(self, request, obj, form, change):
        if obj.pk == request.user.pk and (not obj.is_active or not obj.administra):
            raise PermissionDenied('No se puede desactivar o degradar su propia cuenta.')
        obj.is_staff = obj.administra
        obj.is_superuser = obj.administra
        super().save_model(request, obj, form, change)

class EventoAdmin(admin.ModelAdmin):
    list_display = ['fecha', 'actor', 'accion', 'entidad', 'objeto_id']
    readonly_fields = ['fecha', 'actor', 'accion', 'entidad', 'objeto_id']
    actions = None
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False

municipal_site.register(Usuario, UsuarioAdmin)
municipal_site.register(Delegacion, ConservacionAdmin)
municipal_site.register(Evento, EventoAdmin)

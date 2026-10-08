from apps.cuentas.admin import municipal_site
from django.contrib.auth import views as auth_views
from django.urls import path
from . import views
from apps.agenda import views as agenda_views
from apps.reportes import views as reporte_views

urlpatterns = [
    path('admin/', municipal_site.urls),
    path('acceso/', auth_views.LoginView.as_view(), name='login'),
    path('salir/', auth_views.LogoutView.as_view(), name='logout'),
    path('sesion/actividad/', views.actividad, name='actividad'),
    path('', views.inicio, name='inicio'),
    path('vecinos/', views.vecinos, name='vecinos'),
    path('vecinos/nuevo/', views.vecino_editar, name='vecino_crear'),
    path('vecinos/<int:pk>/editar/', views.vecino_editar, name='vecino_editar'),
    path('solicitudes/', views.solicitudes, name='solicitudes'),
    path('solicitudes/nueva/', views.solicitud_crear, name='solicitud_crear'),
    path('solicitudes/<int:pk>/', views.solicitud_detalle, name='solicitud_detalle'),
    path('solicitudes/<int:pk>/estado/', views.solicitud_transicion, name='solicitud_transicion'),
    path('solicitudes/<int:pk>/observacion/', views.solicitud_observacion, name='solicitud_observacion'),
    path('auditoria/', views.auditoria, name='auditoria'),
    path('agenda/', agenda_views.agenda, name='agenda'),
    path('agenda/nueva/', agenda_views.cita_crear, name='cita_crear'),
    path('agenda/<int:pk>/', agenda_views.cita_detalle, name='cita_detalle'),
    path('agenda/<int:pk>/estado/', agenda_views.cita_estado, name='cita_estado'),
    path('reportes/', reporte_views.reportes, name='reportes'),
]

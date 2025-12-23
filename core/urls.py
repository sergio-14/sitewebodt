from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from controlodt import views

from django.shortcuts import render

from django.conf.urls import handler403
from django.shortcuts import render


def error_403_view(request, exception):
    return render(request, '403.html', status=403)

handler403 = error_403_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    
    #servicios de autenticación
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),

    #usuarios
    path("usuarios/", views.listar_user, name="listar_user"),
    path("usuarios/crear/",views.user_create, name="user_create"),
    path("usuarios/<int:pk>/editar/", views.user_edit, name="user_edit"),
    path("usuarios/<int:pk>/toggle/", views.toggle_active_user, name="user_toggle_active"),
    path('mi-perfil/', views.mi_perfil, name='mi_perfil'),
     
    
    #grupos
    path("grupos/", views.group_list, name="group_list"),
    path("grupos/crear/", views.group_create, name="group_create"),
    path("grupos/<int:pk>/editar/", views.group_edit, name="group_edit"),

    # ============== TIPO MAQUINARIA =================
    path("tipos/", views.tipo_list, name="tipo_list"),
    path("tipos/nuevo/", views.tipo_create, name="tipo_create"),
    path("tipos/<int:pk>/editar/", views.tipo_edit, name="tipo_edit"),
    path("tipos/<int:pk>/toggle/", views.tipo_toggle, name="tipo_toggle"),

    # ============== MAQUINARIA =================
    path("maquinaria/", views.maquinaria_list, name="maquinaria_list"),
    path("maquinaria/nuevo/", views.maquinaria_create, name="maquinaria_create"),
    path("maquinaria/<int:pk>/editar/", views.maquinaria_edit, name="maquinaria_edit"),
    path("maquinaria/<int:pk>/toggle/", views.maquinaria_toggle, name="maquinaria_toggle"),
    path('detalle/<int:pk>/pdf/', views.odt_detalle_pdf, name='odt_detalle_pdf'),

     path('odt/', views.odt_list, name='odt_list'),
    
    # Crear ODT
    path('odt/crear/', views.odt_create, name='odt_create'),
    
    # Detalle ODT
    path('odt/<int:pk>/', views.odt_detail, name='odt_detail'),
    
    # Enviar a solicitud (creador)
    path('odt/<int:pk>/enviar-solicitud/', views.odt_enviar_solicitud, name='odt_enviar_solicitud'),
    
    # Asignar responsable (autorizado)
    path('odt/<int:pk>/asignar/', views.odt_asignar_responsable, name='odt_asignar'),
    
    # Iniciar ejecución (responsable)
    path('odt/<int:pk>/iniciar/', views.odt_iniciar_ejecucion, name='odt_iniciar'),
    
    # Ejecutar/completar detalles (responsable)
    path('odt/<int:pk>/ejecutar/', views.odt_ejecutar, name='odt_ejecutar'),
    
    # Finalizar ejecución (responsable)
    path('odt/<int:pk>/finalizar/', views.odt_finalizar_ejecucion, name='odt_finalizar'),
    
    # Revisar ODT (revisor)
    path('odt/<int:pk>/revisar/', views.odt_revisar, name='odt_revisar'),
    
    # Aprobación final
    path('odt/<int:pk>/aprobar-final/', views.odt_aprobar_final, name='odt_aprobar_final'),
    
    path('odt/<int:pk>/editar-general/', views.odt_editar_general, name='odt_editar_general'),


    path('reportes/odt/', views.reporte_odt_view, name='reporte_odt'),
    path('reportes/odt/pdf/', views.reporte_odt_pdf, name='reporte_odt_pdf'),
    path('reporte-odt-excel/', views.reporte_odt_excel, name='reporte_odt_excel'),

    
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)



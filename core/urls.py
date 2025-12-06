from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from controlodt import views

from django.shortcuts import render

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
    
    #grupos
    path("grupos/", views.group_list, name="group_list"),
    path("grupos/crear/", views.group_create, name="group_create"),
    path("grupos/<int:pk>/editar/", views.group_edit, name="group_edit"),

    # TipoMaquinaria
    path('tipos/', views.tipo_list, name='tipo_list'),
    path('tipos/nuevo/', views.tipo_create, name='tipo_create'),
    path('tipos/<int:pk>/editar/', views.tipo_edit, name='tipo_edit'),

    # Maquinaria
    path('maquinarias/', views.maquinaria_list, name='maquinaria_list'),
    path('maquinarias/nuevo/', views.maquinaria_create, name='maquinaria_create'),
    path('maquinarias/<int:pk>/editar/', views.maquinaria_edit, name='maquinaria_edit'),

    # ODT
    path('odts/', views.odt_list, name='odt_list'),
    path('odts/nuevo/', views.odt_create, name='odt_create'),
    path('odts/<int:pk>/editar/', views.odt_edit, name='odt_edit'),
    path('odts/<int:pk>/', views.odt_detail, name='odt_detail'),

    # Acciones
    path('odts/<int:pk>/request_review/', views.odt_request_review, name='odt_request_review'),
    path('odts/<int:pk>/mark_review/', views.odt_mark_review, name='odt_mark_review'),
    path('odts/<int:pk>/approve/', views.odt_approve, name='odt_approve'),

    # Notificaciones
    path('mis-notificaciones/', views.mis_notificaciones, name='mis_notificaciones'),

    path('odt/revisar/<int:pk>/aprobar/', views.odt_aprobar_revision, name='odt_aprobar_revision'),
    path('odt/revisar/<int:pk>/denegar/', views.odt_denegar_revision, name='odt_denegar_revision'),
    
    # URLs de Acción para Jefe de Área
    path('odt/aprobar/<int:pk>/aprobar/', views.odt_aprobar, name='odt_approve'), 
    path('odt/aprobar/<int:pk>/denegar/', views.odt_denegar_aprobacion, name='odt_denegar_aprobacion'),

    path('detalle/<int:pk>/pdf/', views.odt_detalle_pdf, name='odt_detalle_pdf'),
    
    
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)



from django.contrib import admin
from .models import User, TipoMaquinaria, Maquinaria, RegistroODT
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ['-date_joined']
    list_display = ('email', 'nombre', 'apellido', 'is_active', 'is_staff', 'date_joined', 'updated_at')
    search_fields = ('email', 'nombre', 'apellido', 'dni')

   
    readonly_fields = ('last_login', 'date_joined', 'updated_at')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Información personal'), {
            'fields': ('nombre', 'apellido', 'apellidoM', 'dni', 'telefono', 'direccion', 'imagen')
        }),
        (_('Permisos'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        (_('Fechas'), {
           
            'fields': ('last_login', 'date_joined', 'updated_at')
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'nombre', 'apellido', 'password1', 'password2', 'is_active', 'is_staff'),
        }),
    )



admin.site.register(TipoMaquinaria)
admin.site.register(Maquinaria)
admin.site.register(RegistroODT)

# Register your models here.

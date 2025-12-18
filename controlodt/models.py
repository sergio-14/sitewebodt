from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.db.models import Max


# --- Manager ---
class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_('El correo electrónico es obligatorio'))
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        if not password:
            raise ValueError(_('La contraseña es obligatoria'))
        user.set_password(password)
        
        if 'is_active' not in extra_fields:
            user.is_active = True
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser debe tener is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser debe tener is_superuser=True.'))

        return self.create_user(email, password, **extra_fields)


# --- Model ---
class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(_('Correo electrónico'), unique=True, db_index=True)
    imagen = models.ImageField(_('Foto de perfil'), upload_to='perfil/', null=True, blank=True)
    firma = models.ImageField(_('Firma'), upload_to='firma/', null=True, blank=True)  
    nombre = models.CharField(_('Nombre'), max_length=50)
    apellido = models.CharField(_('Apellido paterno'), max_length=50)
    apellidoM = models.CharField(_('Apellido materno'), max_length=50, null=True, blank=True)

    dni = models.CharField(
        _('Carnet de identidad'),
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text=_('Sin puntos ni espacios'),
    )

    telefono = models.CharField(
        _('Teléfono'),
        max_length=20,
        null=True,
        blank=True,
        validators=[RegexValidator(r'^[0-9+\-\s()]{6,20}$', _('Formato de teléfono inválido'))],
    )
    direccion = models.CharField(_('Dirección'), max_length=255, null=True, blank=True)

    is_active = models.BooleanField(_('Activo'), default=True)
    is_staff = models.BooleanField(_('Staff'), default=False)

    date_joined = models.DateTimeField(_('Fecha de registro'), default=timezone.now)
    updated_at = models.DateTimeField(_('Última actualización'), auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nombre', 'apellido']

    class Meta:
        verbose_name = _('Usuario')
        verbose_name_plural = _('Usuarios')
        ordering = ['-date_joined']
        permissions = [
            ("usuarios", "Permiso para usuarios"),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=['dni'],
                condition=Q(dni__isnull=False),
                name='unique_dni_when_not_null'
            )
        ]

    def clean(self):
        super().clean()
        if self.email:
            self.email = self.email.lower().strip()

    def get_full_name(self):
        parts = [self.nombre, self.apellido, self.apellidoM or '']
        return ' '.join(p for p in parts if p).strip()

    def get_short_name(self):
        return self.nombre

    def __str__(self):
        return self.get_full_name()


class TipoMaquinaria(models.Model):
    """Tipo o familia de maquinaria (por ejemplo: excavadora, generador, bomba)"""
    nombre = models.CharField(_('Nombre'), max_length=100, unique=True)
    activo = models.BooleanField(_('Activo'), default=True)

    class Meta:
        verbose_name = _('Línea')
        verbose_name_plural = _('Líneas de trabajo')
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Maquinaria(models.Model):
    """Registro de cada equipo / máquina"""
    class Estado(models.TextChoices):
        OPERATIVA = 'OPERATIVA', _('Operativa')
        MANTENIMIENTO = 'MANTENIMIENTO', _('Mantención requerida')
        EN_MANTENIMIENTO = 'EN_MANTENIMIENTO', _('En mantención')
        FUERA_SERVICIO = 'FUERA_SERVICIO', _('Fuera de servicio')
        DADO_BAJA = 'DADO_BAJA', _('Dado de baja')

    tipo = models.ForeignKey(TipoMaquinaria, on_delete=models.PROTECT, related_name='maquinarias', verbose_name=_('Tipo'))
    nombre = models.CharField(_('Nombre/Modelo'), max_length=150)
    codigo = models.CharField(_('Código / Placa / Serie'), max_length=100, unique=True, db_index=True)
    descripcion = models.TextField(_('Descripción'), blank=True, null=True)
    estado = models.CharField(_('Estado'), max_length=20, choices=Estado.choices, default=Estado.OPERATIVA, db_index=True)
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='maquinarias_responsable', verbose_name=_('Responsable'))
    activo = models.BooleanField(_('Activo'), default=True)

    class Meta:
        verbose_name = _('Equipo de Trabajo')
        verbose_name_plural = _('Equipos de Trabajo')
        ordering = ['tipo', 'nombre']
        constraints = [
            models.UniqueConstraint(fields=['codigo'], name='unique_maquinaria_codigo')
        ]

    def __str__(self):
        return f'{self.nombre} ({self.codigo})'

    def needs_ot_creation(self, previous_estado: str | None) -> bool:
        """
        Determina si se debe generar automáticamente una ODT basándonos
        en el cambio de estado.
        """
        triggers = {self.Estado.MANTENIMIENTO, self.Estado.FUERA_SERVICIO}
        return (previous_estado not in triggers) and (self.estado in triggers)


class RegistroODT(models.Model):
    """Orden de Trabajo / Registro ODT"""
    class EstadoODT(models.TextChoices):
        BORRADOR = 'BORRADOR', _('Borrador')
        SOLICITUD = 'SOLICITUD', _('En Solicitud')
        ASIGNADA = 'ASIGNADA', _('Asignada')
        EN_EJECUCION = 'EN_EJECUCION', _('En ejecución')
        REVISION = 'REVISION', _('revisado')
        APROBADA = 'APROBADA', _('Aprobada')
        RECHAZADA = 'RECHAZADA', _('R. por Revisión')
        RECHAZADAA = 'RECHAZADAA', _('R. en Aprobación')
        CERRADA = 'CERRADA', _('Cerrada')

    prioridad_choices = [
        ('BAJA', _('Baja')),
        ('MEDIA', _('Media')),
        ('ALTA', _('Alta')),
        ('URGENTE', _('Urgente')),
    ]

    maquinaria = models.ForeignKey(Maquinaria, on_delete=models.CASCADE, related_name='odts', verbose_name=_('Maquinaria'))
    titulo = models.CharField(_('Título'), max_length=200)
    descripcion = models.TextField(_('Descripción del trabajo'))
    estado = models.CharField(_('Estado'), max_length=20, choices=EstadoODT.choices, default=EstadoODT.BORRADOR, db_index=True)
    prioridad = models.CharField(_('Prioridad'), max_length=10, choices=prioridad_choices, default='MEDIA')
    parte_equipo = models.CharField(_('Parte Equipo'), max_length=200)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='odts_creadas', verbose_name=_('Creado por'))
    revisado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='odts_revisadas', verbose_name=_('Revisado por'))
    aprobado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='odts_aprobadas', verbose_name=_('Aprobado por'))
    correlativo = models.PositiveIntegerField(unique=True, editable=False, null=True)
    n_odt = models.PositiveIntegerField(unique=True, editable=False, null=True)
    fecha_programada = models.DateTimeField(_('Fecha/Hora programada'), null=True, blank=True)
    fecha_inicio = models.DateTimeField(_('Fecha/Hora inicio'), null=True, blank=True)
    fecha_termino = models.DateTimeField(_('Fecha/Hora termino'), null=True, blank=True)

    archivo_informe = models.FileField(_('Archivo informe'), upload_to='odt/informes/', null=True, blank=True)

    creado_en = models.DateTimeField(_('Creado'), auto_now_add=True)
    actualizado_en = models.DateTimeField(_('Actualizado'), auto_now=True)

    class Meta:
        verbose_name = _('Registro ODT')
        verbose_name_plural = _('Registros ODT')
        permissions = [
            ("estadisticas", "Permiso para Estadisticas"),
        ]
        ordering = ['-creado_en']
        indexes = [
            models.Index(fields=['estado']),
            models.Index(fields=['prioridad']),
        ]

    def __str__(self):
        return f'ODT #{self.pk} - {self.titulo} [{self.get_estado_display()}]'

    # --- Métodos de Acción de Flujo de Trabajo ---

    def marcar_revision(self, usuario):
        """Operador solicita revisión: pasa a REVISION, creador queda igual."""
        self.estado = self.EstadoODT.REVISION
        self.save(update_fields=['estado'])

    

    def aprobar_revision(self, usuario):
        """Supervisor aprueba: asigna revisor y pasa a REVISION (pendiente Jefe de Área)"""
        self.revisado_por = usuario
        self.estado = self.EstadoODT.REVISION
        self.save(update_fields=['revisado_por', 'estado'])

    def denegar_revision(self):
        """Supervisor deniega la revisión. Borra el campo revisado_por y regresa a EN_EJECUCION."""
        self.revisado_por = None
        self.estado = self.EstadoODT.RECHAZADA
        self.save(update_fields=['revisado_por', 'estado'])

    def aprobar_odt(self, usuario):
        """Jefe de Área aprueba la ODT. Registra al jefe y cambia el estado a APROBADA."""
        self.aprobado_por = usuario
        self.estado = self.EstadoODT.APROBADA
        self.save(update_fields=['aprobado_por', 'estado'])

    def denegar_aprobacion(self):
        """Jefe de Área deniega la aprobación. Borra el aprobado_por y cambia el estado a RECHAZADA."""
        self.aprobado_por = None
        self.estado = self.EstadoODT.RECHAZADAA
        self.save(update_fields=['aprobado_por', 'estado'])

    def save(self, *args, **kwargs):
        if not self.correlativo:
            self.correlativo = (RegistroODT.objects.aggregate(
                Max('correlativo')
            )['correlativo__max'] or 0) + 1

        if not self.n_odt:
            self.n_odt = (RegistroODT.objects.aggregate(
                Max('n_odt')
            )['n_odt__max'] or 0) + 1

        super().save(*args, **kwargs)
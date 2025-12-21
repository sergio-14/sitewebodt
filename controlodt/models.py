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


# =========================
#     TIPO MAQUINARIA
# =========================
class TipoMaquinaria(models.Model):
    nombre = models.CharField(_('Nombre'), max_length=100, unique=True)
    activo = models.BooleanField(_('Activo'), default=True)

    class Meta:
        verbose_name = _('Línea')
        verbose_name_plural = _('Líneas de trabajo')
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


# =========================
#        MAQUINARIA
# =========================
class Maquinaria(models.Model):
    nombre = models.CharField(_('Nombre/Modelo'), max_length=150)
    codigo = models.CharField(_('Código / Placa / Serie'), max_length=100, unique=True, db_index=True)
    descripcion = models.TextField(_('Descripción'), blank=True, null=True)
    activo = models.BooleanField(_('Activo'), default=True)

    class Meta:
        verbose_name = _('Equipo de Trabajo')
        verbose_name_plural = _('Equipos de Trabajo')
        ordering = ['nombre']
        constraints = [
            models.UniqueConstraint(fields=['codigo'], name='unique_maquinaria_codigo')
        ]

    def __str__(self):
        return f'{self.nombre} ({self.codigo})'


# =========================
#        CHOICES
# =========================
class TipoTrabajo(models.TextChoices):
    PREVENTIVO = 'PREVENTIVO', _('Preventivo')
    CORRECTIVO = 'CORRECTIVO', _('Correctivo')


class FallaEquipo(models.TextChoices):
    MECANICO = 'MECANICO', _('Mecánico')
    ELECTRICO = 'ELECTRICO', _('Eléctrico')
    TERMICO = 'TERMICO', _('Térmico')
    HIDRAULICO = 'HIDRAULICO', _('Hidráulico')
    NEUMATICO = 'NEUMATICO', _('Neumático')
    OTRO = 'OTRO', _('Otro')


# =========================
#        REGISTRO ODT
# =========================
class RegistroODT(models.Model):
    class EstadoODT(models.TextChoices):
        BORRADOR = 'BORRADOR', _('Borrador')
        SOLICITUD = 'SOLICITUD', _('En Solicitud')
        ASIGNADA = 'ASIGNADA', _('Asignada')
        EN_EJECUCION = 'EN_EJECUCION', _('En ejecución')
        REVISION = 'REVISION', _('Revisado')
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

    tipo = models.ForeignKey(TipoMaquinaria, on_delete=models.PROTECT, related_name='tipoodts', verbose_name=_('Tipo'))
    maquinaria = models.ForeignKey(Maquinaria, on_delete=models.CASCADE, related_name='odts', verbose_name=_('Maquinaria'))

    titulo = models.CharField(_('Título'), max_length=200)
    descripcion = models.TextField(_('Descripción del trabajo'))

    estado = models.CharField(_('Estado'), max_length=20, choices=EstadoODT.choices,
                              default=EstadoODT.BORRADOR, db_index=True)

    prioridad = models.CharField(_('Prioridad'), max_length=10, choices=prioridad_choices, default='MEDIA')

    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                   related_name='odts_creadas', verbose_name=_('Creado por'))

    revisado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='odts_revisadas', verbose_name=_('Revisado por'))

    aprobado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='odts_aprobadas', verbose_name=_('Aprobado por'))

    # ======= NUEVOS CAMPOS =======
    tipo_trabajo = models.CharField(_('Tipo de trabajo'), max_length=12,
                                    choices=TipoTrabajo.choices, default=TipoTrabajo.PREVENTIVO)

    responsable_ejecucion = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                              null=True, blank=True, related_name='odts_responsable',
                                              verbose_name=_('Responsable de ejecución'))

    autorizado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                       null=True, blank=True, related_name='odts_autorizadas',
                                       verbose_name=_('Autorizado por'))

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
        ordering = ['-creado_en']
        permissions = [
            ("estadisticas", "Permiso para Estadisticas"),
            ("editar_completo_odt", "Puede editar completamente una ODT"),
            ("revisar_odt", "Puede revisar ODTs"),
            ("aprobar_odt", "Puede aprobar ODTs"),
            ("autorizar_odt", "Puede autorizar ODTs"),
            ("detalle_odt", "Puede ver el detalle odt"),
            ("enviar_solicitud", "Puede enviar solicitud"),
            ("mantenimiento_odt", "Puede Llenar mantenimiento"),
        ]
        indexes = [
            models.Index(fields=['estado']),
            models.Index(fields=['prioridad']),
        ]

    def __str__(self):
        return f'ODT #{self.pk} - {self.titulo} [{self.get_estado_display()}]'

    def marcar_revision(self, usuario):
        self.estado = self.EstadoODT.REVISION
        self.save(update_fields=['estado'])

    def aprobar_odt(self, usuario):
        self.aprobado_por = usuario
        self.estado = self.EstadoODT.APROBADA
        self.save(update_fields=['aprobado_por', 'estado'])

    def denegar_aprobacion(self):
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


# =========================
#   DETALLE EJECUCIÓN
# =========================
class DetalleEjecucion(models.Model):
    registro = models.OneToOneField(RegistroODT, on_delete=models.CASCADE, related_name='detalle_ejecucion')

    descripcion_falla = models.TextField(_('Descripción de la falla'), null=True, blank=True)
    falla_tipo = models.CharField(_('Falla del equipo'), max_length=12,
                                  choices=FallaEquipo.choices, default=FallaEquipo.OTRO)

    hora_inicio_trabajo = models.DateTimeField(_('Hora de inicio del trabajo'), null=True, blank=True)
    hora_fin_trabajo = models.DateTimeField(_('Hora de finalización del trabajo'), null=True, blank=True)

    tareas_realizadas = models.TextField(_('Tareas realizadas'), null=True, blank=True)

    medidas_seguridad = models.TextField(_('Medidas de seguridad'), null=True, blank=True)
    observaciones = models.TextField(_('Observaciones'), null=True, blank=True)

    ejecutado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                      null=True, blank=True, related_name='odts_ejecutadas',
                                      verbose_name=_('Ejecutado por'))

    firmado_fecha = models.DateTimeField(_('Fecha firma/Finalización'), null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.ejecutado_por and self.registro.autorizado_por:
            self.ejecutado_por = self.registro.autorizado_por
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Detalle Ejecución ODT #{self.registro.pk}'


# =========================
#        REPUESTOS
# =========================
class Repuesto(models.Model):
    registro = models.ForeignKey(RegistroODT, on_delete=models.CASCADE, related_name='repuestos')
    codigo = models.CharField(_('Código'), max_length=100, null=True, blank=True)
    descripcion = models.CharField(_('Descripción del repuesto'), max_length=255)
    cantidad_utilizada = models.DecimalField(_('Cantidad utilizada'), max_digits=8, decimal_places=2, default=0)

    def __str__(self):
        return f'{self.codigo or ""} - {self.descripcion} ({self.cantidad_utilizada})'


# =========================
#  PERSONAL NECESARIO
# =========================
class PersonalNecesario(models.Model):
    registro = models.ForeignKey(RegistroODT, on_delete=models.CASCADE, related_name='personal_necesario')
    categoria = models.CharField(_('Categoría'), max_length=120, null=True, blank=True)
    trabajador = models.CharField(_('Trabajador'), max_length=120, null=True, blank=True)
    horas_trabajadas = models.DecimalField(_('Horas trabajadas'), max_digits=6, decimal_places=2, default=0)

    def __str__(self):
        if self.trabajador:
            return f'{self.trabajador} - {self.horas_trabajadas}h'
        return f'{self.categoria or "Sin categoría"} - {self.horas_trabajadas}h'
        
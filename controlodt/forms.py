from django import forms
from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from .models import User

from django.contrib.auth.models import Group, Permission

# =========================
# Mixin de estilos Tailwind
# =========================
class TailwindFormMixin:
    """
    Aplica clases Tailwind coherentes a los widgets del form.
    - Estilo base por tipo de widget
    - Marca errores con borde rojo y fondo suave
    - Fuerza HTML5 para date/time/datetime
    - Autocomplete sensato (email/password)
    - Placeholder por defecto = label del campo
    """

    # Clases base
    input_class     = "w-full bg-neutral-50 h-11 rounded-xl border border-neutral-300 px-3 focus:outline-none focus:ring-2 focus:ring-neutral-300"
    textarea_class  = "w-full rounded-xl bg-neutral-50 border border-neutral-300 px-3 py-2 min-h-[70px] max-h-[100px] focus:outline-none focus:ring-2 focus:ring-neutral-300"
    select_class    = "w-full h-11 rounded-xl border border-neutral-300 px-3 bg-neutral-50 focus:outline-none focus:ring-2 focus:ring-neutral-300"
    checkbox_class  = "rounded border-neutral-300 text-neutral-900 focus:ring-neutral-300"
    radio_class     = "text-neutral-900 focus:ring-neutral-300"
    file_class      = "block w-full text-sm bg-neutral-50 text-neutral-700 file:mr-4 file:rounded-lg file:border-0 file:bg-neutral-900 file:px-4 file:py-2 file:text-white hover:file:opacity-90"

    # Estados
    invalid_class   = "border-red-500 bg-red-50 focus:ring-red-500"
    disabled_class  = "bg-neutral-100 text-neutral-500 cursor-not-allowed"

    # Clases auxiliares para render (por si las usas en plantillas)
    label_class     = "block text-sm font-medium mb-1 text-neutral-800"
    help_text_class = "text-xs text-neutral-500 mt-1"
    error_text_class= "text-sm text-red-600 mt-1"

    # Si no quieres ":" automático en labels
    label_suffix = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():
            w = field.widget

            # 1) Clases por tipo
            base = self._class_for_widget(w)
            self._append_classes(w, base)

            # 2) Estados: error / disabled / required
            if self.errors.get(name):
                self._append_classes(w, self.invalid_class)
            if getattr(field, "disabled", False) or w.attrs.get("disabled"):
                self._append_classes(w, self.disabled_class)
            if field.required:
                w.attrs.setdefault("required", True)

            # 3) Placeholder por defecto
            if isinstance(w, (forms.TextInput, forms.EmailInput, forms.URLInput,
                              forms.PasswordInput, forms.NumberInput,
                              forms.DateInput, forms.TimeInput, forms.DateTimeInput,
                              forms.Textarea)):
                w.attrs.setdefault("placeholder", field.label)

            # 4) HTML5 input types y autocomplete
            if isinstance(w, forms.DateInput):
                w.input_type = "date"
            if isinstance(w, forms.TimeInput):
                w.input_type = "time"
            if isinstance(w, forms.DateTimeInput):
                w.input_type = "datetime-local"
            if isinstance(w, forms.EmailInput):
                w.attrs.setdefault("autocomplete", "email")
            if isinstance(w, forms.PasswordInput):
                w.attrs.setdefault("autocomplete", "current-password")

            # 5) Clases auxiliares (útiles si haces includes)
            w.attrs.setdefault("data-label-class", self.label_class)
            w.attrs.setdefault("data-help-class", self.help_text_class)
            w.attrs.setdefault("data-error-class", self.error_text_class)

    # ---- helpers internos ----
    def _class_for_widget(self, widget):
        if isinstance(widget, (forms.TextInput, forms.EmailInput, forms.URLInput,
                               forms.PasswordInput, forms.NumberInput)):
            return self.input_class
        if isinstance(widget, forms.Textarea):
            return self.textarea_class
        if isinstance(widget, (forms.Select, forms.SelectMultiple)):
            return self.select_class
        if isinstance(widget, forms.CheckboxInput):
            return self.checkbox_class
        if isinstance(widget, forms.RadioSelect):
            return self.radio_class
        if isinstance(widget, (forms.ClearableFileInput, forms.FileInput)):
            return self.file_class
        if isinstance(widget, (forms.DateInput, forms.TimeInput, forms.DateTimeInput)):
            return self.input_class
        return self.input_class

    def _append_classes(self, widget, classes_to_add: str):
        existing = widget.attrs.get("class", "").split()
        for c in classes_to_add.split():
            if c not in existing:
                existing.append(c)
        widget.attrs["class"] = " ".join(existing)


# ==================
# Formulario: Login
# ==================
class LoginEmailForm(TailwindFormMixin, forms.Form):
    email = forms.EmailField(label=_("Correo electrónico"), widget=forms.EmailInput())
    password = forms.CharField(label=_("Contraseña"), widget=forms.PasswordInput(render_value=False))
    remember_me = forms.BooleanField(label=_("Recordarme"), required=False)

    error_messages = {
        "invalid_login": _("Correo o contraseña inválidos."),
        "inactive": _("Tu cuenta está inactiva."),
    }

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        email = cleaned.get("email")
        password = cleaned.get("password")
        if email and password:
            user = authenticate(self.request, email=email, password=password)
            if user is None:
                raise forms.ValidationError(self.error_messages["invalid_login"])
            if not user.is_active:
                raise forms.ValidationError(self.error_messages["inactive"])
            self.user_cache = user
        return cleaned

    def get_user(self):
        return self.user_cache


# ==================================
# Formularios: Crear / Editar Usuario
# ==================================
class BaseUserForm(TailwindFormMixin, forms.ModelForm):
    remove_image = forms.BooleanField(label=_("Quitar imagen actual"), required=False)
    
    groups = forms.ModelMultipleChoiceField(
        label=_("Grupos"),
        queryset=Group.objects.all().order_by("name"),
        required=False,
        widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = User
      
        fields = [
            "imagen",
            "firma",
            "nombre", "apellido", "apellidoM",
            "email", "dni", "telefono", "direccion",
           
            "groups",
        ]
        widgets = {
            "nombre": forms.TextInput(attrs={"placeholder": "Nombre"}),
            "apellido": forms.TextInput(attrs={"placeholder": "Apellido paterno"}),
            "apellidoM": forms.TextInput(attrs={"placeholder": "Apellido materno"}),
            "email": forms.EmailInput(attrs={"placeholder": "tucorreo@ejemplo.com"}),
            "dni": forms.TextInput(attrs={"placeholder": "C.I."}),
            "telefono": forms.TextInput(attrs={"placeholder": " 765..."}),
            "direccion": forms.TextInput(attrs={"placeholder": "Dirección"}),
        }

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").lower().strip()
        qs = User.objects.filter(email__iexact=email)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(_("Ya existe un usuario con este correo."))
        return email

    def clean_dni(self):
        dni = (self.cleaned_data.get("dni") or "").strip()
        if not dni:
            return dni
        qs = User.objects.filter(dni__iexact=dni)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(_("Ya existe un usuario con este C.I."))
        return dni


class UserCreateForm(BaseUserForm):
    password1 = forms.CharField(
        label=_("Contraseña"),
        widget=forms.PasswordInput(render_value=False, attrs={"autocomplete": "new-password", "placeholder": "••••••••"})
    )
    password2 = forms.CharField(
        label=_("Confirmar contraseña"),
        widget=forms.PasswordInput(render_value=False, attrs={"autocomplete": "new-password", "placeholder": "••••••••"})
    )

    class Meta(BaseUserForm.Meta):
        pass


    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if not p1:
            self.add_error("password1", _("La contraseña es obligatoria."))
        if p1 and p2 and p1 != p2:
            self.add_error("password2", _("Las contraseñas no coinciden."))
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        
        # AQUÍ FORZAMOS LOS VALORES SOLO AL CREAR
        user.is_active = True
        user.is_staff = True
        
        if commit:
            user.save()
            self.save_m2m()

        return user


class UserUpdateForm(BaseUserForm):
    password1 = forms.CharField(
        label=_("Nueva contraseña (opcional)"),
        widget=forms.PasswordInput(render_value=False, attrs={"autocomplete": "new-password", "placeholder": "••••••••"}),
        required=False
    )
    password2 = forms.CharField(
        label=_("Confirmar nueva contraseña"),
        widget=forms.PasswordInput(render_value=False, attrs={"autocomplete": "new-password", "placeholder": "••••••••"}),
        required=False
    )

    class Meta(BaseUserForm.Meta):
        pass

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 or p2:
            if p1 != p2:
                self.add_error("password2", _("Las contraseñas no coinciden."))
        return cleaned

    def save(self, commit=True):
       
        user = super().save(commit=False)
        
        p1 = self.cleaned_data.get("password1")
        if p1:
            user.set_password(p1)
            
        if commit:
            user.save()
            self.save_m2m()

        # Gestión de quitar imagen
        if self.cleaned_data.get("remove_image"):
            if user.imagen:
                user.imagen.delete(save=False)
            user.imagen = None
            user.save(update_fields=["imagen"])
            
        return user

from django.contrib.auth.forms import PasswordChangeForm
class MiPerfilForm(TailwindFormMixin, forms.ModelForm):
    email = forms.EmailField(label='Correo electrónico')

    class Meta:
        model = User
        fields = [
            'email',
            'nombre',
            'apellido',
            'apellidoM',
            'dni',
            'telefono',
            'direccion',
            'imagen',
        ]

    def clean_email(self):
        email = self.cleaned_data['email'].lower().strip()
        qs = User.objects.filter(email=email).exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Este correo ya está en uso.")
        return email


class CambiarPasswordForm(TailwindFormMixin, PasswordChangeForm):
    pass



from django.contrib.auth.models import Group, Permission
from django.db.models import Q
from django import forms
from django.conf import settings
from collections import OrderedDict
from django.utils.translation import gettext_lazy as _

EXCLUDED_APPS = {"admin", "contenttypes", "sessions"}

ACTION_LABEL = {
    'add': _('Agregar'),
    'change': _('Modificar'),
    'delete': _('Eliminar'),
    'view': _('Ver'),
    # agrega mapeos para permisos personalizados si los tienes
    # 'usuarios': _('Permiso para usuarios'),
}

class GroupForm(TailwindFormMixin, forms.ModelForm):
    permissions = forms.ModelMultipleChoiceField(
        label=_("Permisos"),
        queryset=Permission.objects.select_related("content_type").all().order_by(
            "content_type__app_label", "content_type__model", "codename"
        ),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = Group
        fields = ["name", "permissions"]
        widgets = {"name": forms.TextInput(attrs={"placeholder": _("Nombre del grupo")})}

    # ---------- helpers ----------
    def _build_allowed_qs(self):
        """
        Define el queryset base de permisos permitidos.
        Si settings.GROUP_PERMISSION_APPS existe, usa esas apps; si no, usa todas excepto EXCLUDED_APPS.
        SIEMPRE incluye permisos del modelo Group (auth.group) para gestionar grupos.
        Siempre incluimos permisos ya asignados al grupo para evitar que se pierdan en edición.
        """
        allowed_apps = getattr(settings, "GROUP_PERMISSION_APPS", None)
        
        # Filtro base según configuración
        if allowed_apps:
            base_filter = Q(content_type__app_label__in=allowed_apps)
        else:
            base_filter = ~Q(content_type__app_label__in=EXCLUDED_APPS)
        
        # IMPORTANTE: Siempre incluir permisos del modelo Group (auth.group)
        group_perms_filter = Q(content_type__app_label='auth', content_type__model='group')
        
        # Combinar filtros: (base_filter OR group_perms)
        combined_filter = base_filter | group_perms_filter

        # Incluir permisos ya asignados al grupo (para edición)
        existing_ids = []
        if getattr(self, "instance", None) and getattr(self.instance, "pk", None):
            existing_ids = list(self.instance.permissions.values_list("pk", flat=True))

        return (Permission.objects.select_related("content_type")
                .filter(combined_filter | Q(pk__in=existing_ids))
                .order_by("content_type__app_label", "content_type__model", "codename"))

    def _ensure_allowed_qs(self):
        if not hasattr(self, "allowed_qs"):
            self.allowed_qs = self._build_allowed_qs()

    # ---------- init ----------
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ensure_allowed_qs()

        # --- Construir estructura agrupada por modelo (para template) ---
        grouped = OrderedDict()
        for perm in self.allowed_qs:
            ct = perm.content_type
            # intentar obtener verbose_name del modelo
            try:
                model_cls = ct.model_class()
                if model_cls:
                    model_verbose = getattr(model_cls._meta, 'verbose_name', ct.model).capitalize()
                    model_verbose_plural = getattr(model_cls._meta, 'verbose_name_plural', model_verbose + 's').capitalize()
                else:
                    model_verbose = ct.model.capitalize()
                    model_verbose_plural = (ct.model + 's').capitalize()
            except Exception:
                model_verbose = ct.model.capitalize()
                model_verbose_plural = (ct.model + 's').capitalize()

            # deducir acción desde el codename (add_xxx, change_xxx, etc.)
            codename = perm.codename  # ej "add_activo" o "usuarios" (perm custom)
            if '_' in codename:
                action_key = codename.split('_', 1)[0]
            else:
                action_key = codename

            action_label = ACTION_LABEL.get(action_key, action_key.capitalize())

            # etiqueta: "Agregar Activo" o para permisos personalizados simplemente mostrar perm.name
            if '_' in perm.codename:
                label = f"{action_label} {model_verbose}"
            else:
                # permiso personalizado (p.ej. "usuarios") -> usa perm.name
                label = perm.name

            key = (ct.app_label, ct.model, model_verbose_plural)
            grouped.setdefault(key, []).append({
                'perm': perm,
                'label': label,
                'action': action_key,
                'model_verbose': model_verbose,
                'model_verbose_plural': model_verbose_plural,
            })

        self.allowed_grouped = grouped
        # --- FIN grouped ---

        # Preselección en edición (tu lógica existente)
        if self.instance and self.instance.pk and not self.is_bound:
            allowed_ids = set(self.allowed_qs.values_list("pk", flat=True))
            current_ids = list(self.instance.permissions.values_list("pk", flat=True))
            initial_ids = [str(pk) for pk in current_ids if pk in allowed_ids]
            self.initial.setdefault("permissions", initial_ids)

    # ---------- propiedad para el template ----------
    @property
    def selected_ids(self):
        """
        IDs (como strings) que deben aparecer marcados:
        - Si el form está bound: lo que viene del POST.
        - Si hay initial: initial.
        - Si es edición y no está bound: los permisos actuales del grupo.
        """
        if self.is_bound:
            return [str(v) for v in self.data.getlist(self.add_prefix("permissions"))]

        if "permissions" in self.initial and self.initial["permissions"]:
            return [str(v) for v in self.initial["permissions"]]

        if self.instance and self.instance.pk:
            return [str(pk) for pk in self.instance.permissions.values_list("pk", flat=True)]

        return []

    # ---------- clean ----------
    def clean_permissions(self):
        self._ensure_allowed_qs()
        raw_vals = self.data.getlist(self.add_prefix("permissions")) if self.is_bound else []
        ids = []
        for v in raw_vals:
            try:
                ids.append(int(str(v).strip()))
            except Exception:
                continue

        allowed_ids = set(self.allowed_qs.values_list("pk", flat=True))
        invalid = [v for v in ids if v not in allowed_ids]
        if invalid:
            raise forms.ValidationError(
                _("Escoja una opción válida. %(invalid)s no es/son parte de las opciones permitidas."),
                params={"invalid": ", ".join(str(i) for i in invalid)},
            )

        return Permission.objects.filter(pk__in=ids)

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if not name:
            raise forms.ValidationError(_("El nombre del grupo es obligatorio."))
        qs = Group.objects.filter(name__iexact=name)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(_("Ya existe un grupo con ese nombre."))
        return name

from .models import TipoMaquinaria, Maquinaria

class TipoMaquinariaForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = TipoMaquinaria
        fields = ['nombre', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'placeholder': 'Nombre del tipo de maquinaria'}),
        }


class MaquinariaForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = Maquinaria
        fields = ['tipo', 'nombre', 'codigo', 'descripcion', 'estado', 'responsable', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'placeholder': 'Nombre / Modelo'}),
            'codigo': forms.TextInput(attrs={'placeholder': 'Código / Placa / Serie'}),
            'descripcion': forms.Textarea(attrs={'placeholder': 'Descripción (opcional)'}),
            'fecha_compra': forms.DateInput(attrs={'placeholder': 'Fecha de compra'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['responsable'].queryset = getattr(self.fields['responsable'], 'queryset', None) or \
            __import__('django').contrib.auth.get_user_model().objects.filter(is_active=True)

        self.fields['tipo'].empty_label = "Seleccione tipo..."


from .models import RegistroODT
class RegistroODTForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = RegistroODT
        fields = [
            'maquinaria',
            'titulo',
            'descripcion',
            'parte_equipo',        # ✅ FALTABA
            'prioridad',
            'fecha_programada',
            'archivo_informe',
        ]
        widgets = {
            'descripcion': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Descripción del trabajo'
            }),
            'parte_equipo': forms.TextInput(attrs={
                'placeholder': 'Ej: Motor, sistema eléctrico, transmisión'
            }),
            'fecha_programada': forms.DateTimeInput(attrs={
                'type': 'datetime-local'
            }),
        }

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.urls import reverse
from .forms import LoginEmailForm

def home(request):
 
    if request.user.is_authenticated:
        return redirect("dashboard")

    show_login_modal = request.GET.get("login") == "1"
    context = {
        "form": LoginEmailForm(),
        "show_login_modal": show_login_modal,
    }
    return render(request, "home.html", context)


def login_view(request):
    if request.method == "POST":
        form = LoginEmailForm(request=request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            # Remember me
            if form.cleaned_data.get("remember_me"):
                request.session.set_expiry(60 * 60 * 24 * 14)  
            else:
                request.session.set_expiry(0)  

            next_url = request.POST.get("next") or reverse("dashboard")
            return redirect(next_url)
        else:
         
            messages.error(request, "Revisa tus credenciales.")
            return render(request, "home.html", {"form": form, "show_login_modal": True})

    
    return redirect(f'{reverse("home")}?login=1')

def logout_view(request):
    logout(request)
    messages.success(request, "Sesión cerrada.")
    return redirect("home")

@login_required
def dashboard(request):
    return render(request, "dashboard.html")


from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.urls import reverse
from .models import User
from .forms import UserCreateForm, UserUpdateForm
from django.utils.http import url_has_allowed_host_and_scheme

@login_required
@permission_required('controlodt.view_user', raise_exception=True)
def listar_user(request):
    q = (request.GET.get("q") or "").strip()
    estado = request.GET.get("estado") or "todos"   
    per_page_options = [8, 20, 30, 50, 100]

    try:
        per_page = int(request.GET.get("per_page") or 10)
    except ValueError:
        per_page = 10
    if per_page not in per_page_options:
        per_page = 10

    users = User.objects.all().order_by("-date_joined")

    if q:
        for t in q.split():
            users = users.filter(
                Q(nombre__icontains=t) |
                Q(apellido__icontains=t) |
                Q(apellidoM__icontains=t) |
                Q(email__icontains=t) |
                Q(dni__icontains=t)
            )

    if estado == "activos":
        users = users.filter(is_active=True)
    elif estado == "inactivos":
        users = users.filter(is_active=False)

    paginator = Paginator(users, per_page)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "page_obj": page_obj,
        "q": q,
        "estado": estado,
        "per_page": per_page,
        "per_page_options": per_page_options,
        "total": paginator.count,
        "current_querystring": request.META.get("QUERY_STRING", ""),
    }
    return render(request, "users/listar_user.html", context)


@login_required

@require_POST
def toggle_active_user(request, pk):
    user = get_object_or_404(User, pk=pk)

    if user == request.user:
        messages.error(request, "No puedes cambiar tu propio estado.")
        return redirect(reverse("listar_user"))

    user.is_active = not user.is_active
    user.save(update_fields=["is_active", "updated_at"])

    messages.success(
        request,
        f"Usuario {'activado' if user.is_active else 'dado de baja'} correctamente."
    )

    base = reverse("listar_user")
    next_url = request.POST.get("next", "")

    if next_url.startswith("?"):
        return redirect(f"{base}{next_url}")

    if next_url and url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure()
    ):
        return redirect(next_url)

   
    return redirect(base)

from .forms import MiPerfilForm, CambiarPasswordForm
from django.contrib.auth import login, logout, update_session_auth_hash

@login_required
def mi_perfil(request):
    user = request.user

    if request.method == 'POST':
        if 'guardar_perfil' in request.POST:
            perfil_form = MiPerfilForm(request.POST, request.FILES, instance=user)
            password_form = CambiarPasswordForm(user)  
            if perfil_form.is_valid():
                perfil_form.save()
                messages.success(request, 'Perfil actualizado correctamente.')
                return redirect('dashboard')

        elif 'cambiar_password' in request.POST:
            perfil_form = MiPerfilForm(instance=user)  
            password_form = CambiarPasswordForm(user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Contraseña actualizada correctamente.')
                return redirect('dashboard')

    else:
        perfil_form = MiPerfilForm(instance=user)
        password_form = CambiarPasswordForm(user)

    return render(request, 'users/mi_perfil.html', {
        'perfil_form': perfil_form,
        'password_form': password_form,
    })

@login_required
@permission_required('controlodt.add_user', raise_exception=True)
def user_create(request):
    next_url = request.GET.get("next") or reverse("listar_user")
    if request.method == "POST":
        form = UserCreateForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Usuario creado correctamente.")
            return redirect(next_url)
    else:
        form = UserCreateForm()
    return render(request, "users/user_form.html", {
        "form": form,
        "title": "Crear usuario",
        "is_edit": False,
        "next_url": next_url,
    })


@login_required
@permission_required('controlodt.change_user', raise_exception=True)
def user_edit(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    next_url = request.GET.get("next") or reverse("listar_user")

    original_is_active = user_obj.is_active

    if request.method == "POST":
        form = UserUpdateForm(request.POST, request.FILES, instance=user_obj)
        if form.is_valid():
            if user_obj.pk == request.user.pk:
                cleaned_is_active = form.cleaned_data.get("is_active")
                if cleaned_is_active is False and original_is_active is True:
                    messages.error(request, "No puedes darte de baja a ti mismo.")
                    saved = form.save(commit=False)
                    saved.is_active = True
                    saved.save()
                    messages.info(request, "Se guardaron otros cambios; el estado se mantuvo activo.")
                    return redirect(next_url)
            form.save()
            messages.success(request, "Usuario actualizado correctamente.")
            return redirect(next_url)
    else:
        form = UserUpdateForm(instance=user_obj)

    return render(request, "users/user_form.html", {
        "form": form,
        "title": "Editar usuario",
        "is_edit": True,
        "user_obj": user_obj,
        "next_url": next_url,
    })
    

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import Group, Permission
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from .forms import GroupForm


@login_required
@permission_required('auth.view_group', raise_exception=True)
def group_list(request):
    q = (request.GET.get("q") or "").strip()
    per_page_options = [8, 20, 30, 50, 100]

   
    try:
        per_page = int(request.GET.get("per_page") or 10)
    except ValueError:
        per_page = 10
    if per_page not in per_page_options:
        per_page = 10

    groups = Group.objects.all().order_by("name")
    if q:
        groups = groups.filter(Q(name__icontains=q))


    paginator = Paginator(groups, per_page)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "page_obj": page_obj,        
        "groups": page_obj,           
        "q": q,
        "per_page": per_page,
        "per_page_options": per_page_options,
        "total": paginator.count,    
        "current_querystring": request.META.get("QUERY_STRING", ""),
    }

    return render(request, "groups/group_list.html", context)

@login_required
@permission_required('auth.add_group', raise_exception=True)
def group_create(request):
    next_url = request.GET.get("next") or reverse("group_list")
    if request.method == "POST":
        form = GroupForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Grupo creado correctamente.")
            return redirect(next_url)
    else:
        form = GroupForm()

    return render(request, "groups/group_form.html", {
        "title": "Crear grupo",
        "form": form,
        "is_edit": False,
        "next_url": next_url,
    })


@login_required
@permission_required('auth.change_group', raise_exception=True)
def group_edit(request, pk):
    group = get_object_or_404(Group, pk=pk)
    next_url = request.GET.get("next") or reverse("group_list")

    if request.method == "POST":
        form = GroupForm(request.POST, instance=group)
        if form.is_valid():
            form.save()
            messages.success(request, "Grupo actualizado correctamente.")
            return redirect(next_url)
    else:
        form = GroupForm(instance=group)

    return render(request, "groups/group_form.html", {
        "title": "Editar grupo",
        "form": form,
        "is_edit": True,
        "group_obj": group,
        "next_url": next_url,
    })


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import TipoMaquinaria, Maquinaria
from .forms import TipoMaquinariaForm, MaquinariaForm


# =======================
#   TIPO MAQUINARIA
# =======================
def tipo_list(request):
    tipos = TipoMaquinaria.objects.all()
    return render(request, "mantenimiento/tipo_list.html", {
        "tipos": tipos,
        "title": "Líneas de Trabajo"
    })


def tipo_create(request):
    if request.method == "POST":
        form = TipoMaquinariaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Registro creado correctamente")
            return redirect("tipo_list")
    else:
        form = TipoMaquinariaForm()

    return render(request, "mantenimiento/tipo_form.html", {
        "form": form,
        "title": "Nueva Línea de Trabajo"
    })


def tipo_edit(request, pk):
    obj = get_object_or_404(TipoMaquinaria, pk=pk)

    if request.method == "POST":
        form = TipoMaquinariaForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Registro actualizado correctamente")
            return redirect("tipo_list")
    else:
        form = TipoMaquinariaForm(instance=obj)

    return render(request, "mantenimiento/tipo_form.html", {
        "form": form,
        "title": "Editar Línea de Trabajo",
        "is_edit": True
    })


def tipo_toggle(request, pk):
    obj = get_object_or_404(TipoMaquinaria, pk=pk)
    obj.activo = not obj.activo
    obj.save()
    return redirect("tipo_list")


# =======================
#       MAQUINARIA
# =======================
def maquinaria_list(request):
    maquinas = Maquinaria.objects.select_related().all()
    return render(request, "mantenimiento/maquinaria_list.html", {
        "maquinas": maquinas,
        "title": "Equipos de Trabajo"
    })


def maquinaria_create(request):
    if request.method == "POST":
        form = MaquinariaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Equipo registrado correctamente")
            return redirect("maquinaria_list")
    else:
        form = MaquinariaForm()

    return render(request, "mantenimiento/maquinaria_form.html", {
        "form": form,
        "title": "Registrar Equipo"
    })


def maquinaria_edit(request, pk):
    obj = get_object_or_404(Maquinaria, pk=pk)

    if request.method == "POST":
        form = MaquinariaForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Equipo actualizado correctamente")
            return redirect("maquinaria_list")
    else:
        form = MaquinariaForm(instance=obj)

    return render(request, "mantenimiento/maquinaria_form.html", {
        "form": form,
        "title": "Editar Equipo",
        "is_edit": True
    })


def maquinaria_toggle(request, pk):
    obj = get_object_or_404(Maquinaria, pk=pk)
    obj.activo = not obj.activo
    obj.save()
    return redirect("maquinaria_list")





from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.db.models import Q
from .models import RegistroODT, DetalleEjecucion
from .forms import (
    ODTCreateForm, ODTAsignarResponsableForm, DetalleEjecucionForm,
    RepuestoFormSet, PersonalFormSet, ODTRevisionForm, ODTAprobacionForm,
    ODTEditGeneralForm  # Nuevo formulario
)


# =========================
# HELPER: Verificar permisos de edición
# =========================

def puede_editar_odt(user, odt):
    """
    Determina si un usuario puede editar una ODT.
    Pueden editar:
    - El que autorizó la ODT
    - El que revisó la ODT
    - Usuarios con permiso 'odt.editar_completo'
    - Superusuarios
    """
    if user.is_superuser:
        return True
    
    # Verificar si tiene el permiso específico
    if user.has_perm('app.editar_completo_odt'):  # Ajusta 'app' al nombre de tu app
        return True
    
    # Verificar si es el autorizado o el revisor
    if odt.autorizado_por == user or odt.revisado_por == user:
        return True
    
    return False


# =========================
# VISTA: Listado de ODTs
# =========================
@login_required
@permission_required('controlodt.view_registroodt', raise_exception=True)
def odt_list(request):
    user = request.user

    # ================= FILTROS =================
    tipo = request.GET.get('tipo')
    maquinaria = request.GET.get('maquinaria')
   
    prioridad = request.GET.get('prioridad')

    # ===== Base queryset según permisos =====
    if user.is_superuser or user.has_perm('controlodt.aprobar_odt') or user.has_perm('controlodt.revisar_odt'):
        odts = RegistroODT.objects.all()
    else:
        odts = RegistroODT.objects.filter(
            Q(creado_por=user) |
            Q(responsable_ejecucion=user) |
            Q(autorizado_por=user) |
            Q(revisado_por=user)
        ).distinct()

    # ===== Aplicar filtros =====
    if tipo:
        odts = odts.filter(tipo_id=tipo)

    if maquinaria:
        odts = odts.filter(maquinaria_id=maquinaria)

  

    if prioridad:
        odts = odts.filter(prioridad=prioridad)

    odts = odts.select_related('tipo', 'maquinaria', 'creado_por', 'responsable_ejecucion').order_by('-creado_en')

    # ===== PAGINACIÓN =====
    paginator = Paginator(odts, 10)   # 🔥 10 por página (cámbialo si quieres)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'title': 'Órdenes de Trabajo',
        'page_obj': page_obj,
        'odts': page_obj.object_list,

        # Enviamos data para combos
        'tipos': TipoMaquinaria.objects.all(),
        'maquinarias': Maquinaria.objects.all(),
        'estados': RegistroODT.EstadoODT.choices,
        'prioridades': RegistroODT.prioridad_choices,
    }

    return render(request, 'odt/odt_list.html', context)


# =========================
# VISTA: Crear ODT
# =========================

@login_required
@permission_required('controlodt.view_registroodt', raise_exception=True)
def odt_create(request):
    """
    Permite a un usuario crear una nueva ODT.
    Estado inicial: BORRADOR
    """
    if request.method == 'POST':
        form = ODTCreateForm(request.POST)
        if form.is_valid():
            odt = form.save(commit=False)
            odt.creado_por = request.user
            odt.estado = RegistroODT.EstadoODT.BORRADOR
            odt.save()
            messages.success(request, f'ODT #{odt.pk} creada exitosamente.')
            return redirect('odt_detail', pk=odt.pk)
    else:
        form = ODTCreateForm()
    
    context = {
        'title': 'Nueva Orden de Trabajo',
        'form': form
    }
    return render(request, 'odt/odt_form.html', context)


# =========================
# VISTA: Detalle ODT
# =========================
@login_required
@permission_required('controlodt.detalle_odt', raise_exception=True)
def odt_detail(request, pk):
    """
    Muestra el detalle completo de una ODT.
    """
    odt = get_object_or_404(RegistroODT, pk=pk)
    
    # Verificar si puede editar
    puede_editar = puede_editar_odt(request.user, odt)
    
    context = {
        'title': f'ODT #{odt.pk}',
        'odt': odt,
        'puede_editar': puede_editar
    }
    return render(request, 'odt/odt_detail.html', context)


# =========================
# VISTA: Edición General ODT (Solo supervisores)
# =========================
@login_required
@transaction.atomic
@permission_required('controlodt.editar_completo_odt', raise_exception=True)
def odt_editar_general(request, pk):
    """
    Permite editar todos los campos de la ODT.
    Solo para usuarios autorizados, revisores o con permisos especiales.
    """
    odt = get_object_or_404(RegistroODT, pk=pk)
    
    # Verificar permisos
    if not puede_editar_odt(request.user, odt):
        messages.error(request, 'No tienes permiso para editar esta ODT.')
        return redirect('odt_detail', pk=pk)
    
    # Obtener o crear DetalleEjecucion si existe
    detalle = None
    if hasattr(odt, 'detalle_ejecucion'):
        detalle = odt.detalle_ejecucion
    
    if request.method == 'POST':
        form_odt = ODTEditGeneralForm(request.POST, instance=odt)
        form_detalle = DetalleEjecucionForm(request.POST, instance=detalle) if detalle else None
        formset_repuestos = RepuestoFormSet(request.POST, instance=odt)
        formset_personal = PersonalFormSet(request.POST, instance=odt)
        
        if form_odt.is_valid() and formset_repuestos.is_valid() and formset_personal.is_valid():
            # Guardar ODT
            odt = form_odt.save()
            
            # Guardar detalle si existe
            if form_detalle and form_detalle.is_valid():
                form_detalle.save()
            
            # Guardar formsets
            formset_repuestos.save()
            formset_personal.save()
            
            messages.success(request, f'ODT #{odt.pk} actualizada exitosamente.')
            return redirect('odt_detail', pk=pk)
    else:
        form_odt = ODTEditGeneralForm(instance=odt)
        form_detalle = DetalleEjecucionForm(instance=detalle) if detalle else None
        formset_repuestos = RepuestoFormSet(instance=odt)
        formset_personal = PersonalFormSet(instance=odt)
    
    context = {
        'title': f'Editar ODT #{odt.pk}',
        'odt': odt,
        'form_odt': form_odt,
        'form_detalle': form_detalle,
        'formset_repuestos': formset_repuestos,
        'formset_personal': formset_personal
    }
    return render(request, 'odt/odt_editar_general.html', context)


# =========================
# VISTA: Enviar a Solicitud
# =========================
@login_required
@permission_required('controlodt.enviar_solicitud', raise_exception=True)
def odt_enviar_solicitud(request, pk):
    """
    El creador envía la ODT para solicitud (para que sea autorizada).
    """
    odt = get_object_or_404(RegistroODT, pk=pk)
    
    if odt.creado_por != request.user:
        messages.error(request, 'No tienes permiso para realizar esta acción.')
        return redirect('odt_detail', pk=pk)
    
    if odt.estado != RegistroODT.EstadoODT.BORRADOR:
        messages.warning(request, 'Esta ODT ya no está en borrador.')
        return redirect('odt_detail', pk=pk)
    
    odt.estado = RegistroODT.EstadoODT.SOLICITUD
    odt.save()
    messages.success(request, f'ODT #{odt.pk} enviada a solicitud.')
    return redirect('odt_detail', pk=pk)


# =========================
# VISTA: Asignar Responsable (Usuario Autorizado)
# =========================
@login_required
@permission_required('controlodt.autorizar_odt', raise_exception=True)
def odt_asignar_responsable(request, pk):
    """
    El usuario "autorizado" asigna el responsable de ejecución y aprueba la ODT.
    Cambia estado a ASIGNADA.
    """
    odt = get_object_or_404(RegistroODT, pk=pk)
    
    # Solo si está en SOLICITUD
    if odt.estado != RegistroODT.EstadoODT.SOLICITUD:
        messages.warning(request, 'Esta ODT no está en estado de solicitud.')
        return redirect('odt_detail', pk=pk)
    
    if request.method == 'POST':
        form = ODTAsignarResponsableForm(request.POST, instance=odt)
        if form.is_valid():
            odt = form.save(commit=False)
            odt.autorizado_por = request.user
            odt.estado = RegistroODT.EstadoODT.ASIGNADA
            odt.save()
            messages.success(request, f'Responsable asignado a ODT #{odt.pk}.')
            return redirect('odt_detail', pk=pk)
    else:
        form = ODTAsignarResponsableForm(instance=odt)
    
    context = {
        'title': f'Asignar Responsable - ODT #{odt.pk}',
        'form': form,
        'odt': odt
    }
    return render(request, 'odt/odt_asignar.html', context)


# =========================
# VISTA: Iniciar Ejecución
# =========================
@login_required
@permission_required('controlodt.mantenimiento_odt', raise_exception=True)
def odt_iniciar_ejecucion(request, pk):
    """
    El responsable de ejecución inicia la ODT.
    Cambia estado a EN_EJECUCION.
    """
    odt = get_object_or_404(RegistroODT, pk=pk)
    
    if odt.responsable_ejecucion != request.user:
        messages.error(request, 'No eres el responsable de esta ODT.')
        return redirect('odt_detail', pk=pk)
    
    if odt.estado != RegistroODT.EstadoODT.ASIGNADA:
        messages.warning(request, 'Esta ODT no está asignada.')
        return redirect('odt_detail', pk=pk)
    
    odt.estado = RegistroODT.EstadoODT.EN_EJECUCION
    odt.fecha_inicio = timezone.now()
    odt.save()
    
    messages.success(request, f'ODT #{odt.pk} en ejecución.')
    return redirect('odt_ejecutar', pk=pk)


# =========================
# VISTA: Ejecutar ODT (Completar Detalles)
# =========================
@login_required
@transaction.atomic
@permission_required('controlodt.mantenimiento_odt', raise_exception=True)
def odt_ejecutar(request, pk):
    """
    El responsable completa los detalles de ejecución, repuestos y personal.
    """
    odt = get_object_or_404(RegistroODT, pk=pk)
    
    if odt.responsable_ejecucion != request.user:
        messages.error(request, 'No eres el responsable de esta ODT.')
        return redirect('odt_detail', pk=pk)
    
    if odt.estado not in [RegistroODT.EstadoODT.EN_EJECUCION, RegistroODT.EstadoODT.RECHAZADA]:
        messages.warning(request, 'Esta ODT no está en ejecución.')
        return redirect('odt_detail', pk=pk)
    
    # Obtener o crear DetalleEjecucion
    detalle, created = DetalleEjecucion.objects.get_or_create(registro=odt)
    
    if request.method == 'POST':
        form_detalle = DetalleEjecucionForm(request.POST, instance=detalle)
        formset_repuestos = RepuestoFormSet(request.POST, instance=odt)
        formset_personal = PersonalFormSet(request.POST, instance=odt)
        
        if form_detalle.is_valid() and formset_repuestos.is_valid() and formset_personal.is_valid():
            # Guardar detalle
            detalle = form_detalle.save(commit=False)
            detalle.ejecutado_por = request.user
            detalle.save()
            
            # Guardar formsets
            formset_repuestos.save()
            formset_personal.save()
            
            messages.success(request, 'Detalles de ejecución guardados.')
            return redirect('odt_detail', pk=pk)
    else:
        form_detalle = DetalleEjecucionForm(instance=detalle)
        formset_repuestos = RepuestoFormSet(instance=odt)
        formset_personal = PersonalFormSet(instance=odt)
    
    context = {
        'title': f'Ejecutar ODT #{odt.pk}',
        'odt': odt,
        'form_detalle': form_detalle,
        'formset_repuestos': formset_repuestos,
        'formset_personal': formset_personal
    }
    return render(request, 'odt/odt_ejecutar.html', context)


# =========================
# VISTA: Finalizar Ejecución (Enviar a Revisión)
# =========================
@login_required
@permission_required('controlodt.autorizar_odt', raise_exception=True)
def odt_finalizar_ejecucion(request, pk):
    """
    El responsable finaliza la ejecución y envía a revisión.
    """
    odt = get_object_or_404(RegistroODT, pk=pk)
    
    if odt.responsable_ejecucion != request.user:
        messages.error(request, 'No eres el responsable de esta ODT.')
        return redirect('odt_detail', pk=pk)
    
    if odt.estado != RegistroODT.EstadoODT.EN_EJECUCION:
        messages.warning(request, 'Esta ODT no está en ejecución.')
        return redirect('odt_detail', pk=pk)
    
    # Verificar que exista detalle de ejecución
    if not hasattr(odt, 'detalle_ejecucion'):
        messages.error(request, 'Debe completar los detalles de ejecución antes de finalizar.')
        return redirect('odt_ejecutar', pk=pk)
    
    odt.estado = RegistroODT.EstadoODT.REVISION
    odt.fecha_termino = timezone.now()
    
    # Actualizar fecha de firma en detalle
    detalle = odt.detalle_ejecucion
    detalle.firmado_fecha = timezone.now()
    detalle.save()
    
    odt.save()
    messages.success(request, f'ODT #{odt.pk} enviada a revisión.')
    return redirect('odt_detail', pk=pk)


# =========================
# VISTA: Revisar ODT
# =========================
@login_required
@permission_required('controlodt.revisar_odt', raise_exception=True)
def odt_revisar(request, pk):
    """
    El revisor aprueba o rechaza la ODT en revisión.
    """
    odt = get_object_or_404(RegistroODT, pk=pk)
    
    if odt.estado != RegistroODT.EstadoODT.REVISION:
        messages.warning(request, 'Esta ODT no está en revisión.')
        return redirect('odt_detail', pk=pk)
    
    if request.method == 'POST':
        form = ODTRevisionForm(request.POST)
        if form.is_valid():
            decision = form.cleaned_data['decision']
            
            if decision == 'aprobar':
                odt.revisado_por = request.user
                odt.estado = RegistroODT.EstadoODT.APROBADA
                odt.save()
                messages.success(request, f'ODT #{odt.pk} aprobada en revisión.')
            else:
                odt.estado = RegistroODT.EstadoODT.RECHAZADA
                odt.save()
                messages.warning(request, f'ODT #{odt.pk} rechazada. Devuelta a ejecución.')
            
            return redirect('odt_detail', pk=pk)
    else:
        form = ODTRevisionForm()
    
    context = {
        'title': f'Revisar ODT #{odt.pk}',
        'odt': odt,
        'form': form
    }
    return render(request, 'odt/odt_revisar.html', context)


# =========================
# VISTA: Aprobación Final
# =========================
@login_required
@permission_required('controlodt.aprobar_odt', raise_exception=True)
def odt_aprobar_final(request, pk):
    """
    Aprobación final de la ODT (puede ser el mismo autorizado u otro usuario).
    """
    odt = get_object_or_404(RegistroODT, pk=pk)
    
    if odt.estado != RegistroODT.EstadoODT.APROBADA:
        messages.warning(request, 'Esta ODT no está lista para aprobación final.')
        return redirect('odt_detail', pk=pk)
    
    if request.method == 'POST':
        form = ODTAprobacionForm(request.POST)
        if form.is_valid():
            decision = form.cleaned_data['decision']
            
            if decision == 'aprobar':
                odt.aprobado_por = request.user
                odt.estado = RegistroODT.EstadoODT.CERRADA
                odt.save()
                messages.success(request, f'ODT #{odt.pk} cerrada exitosamente.')
            else:
                odt.estado = RegistroODT.EstadoODT.RECHAZADAA
                odt.save()
                messages.warning(request, f'ODT #{odt.pk} rechazada en aprobación.')
            
            return redirect('odt_detail', pk=pk)
    else:
        form = ODTAprobacionForm()
    
    context = {
        'title': f'Aprobación Final - ODT #{odt.pk}',
        'odt': odt,
        'form': form
    }
    return render(request, 'odt/odt_aprobar.html', context)




import os
from django.conf import settings
from django.shortcuts import render, get_object_or_404
from django.template.loader import get_template
from django.http import HttpResponse
from urllib.parse import urlparse
from django.conf import settings
from django.contrib.staticfiles import finders

from xhtml2pdf import pisa 

from .models import RegistroODT 
import os
from django.conf import settings


def link_callback(uri, rel):
    """
    Convierte URLs de STATIC y MEDIA en rutas absolutas del sistema
    compatibles con xhtml2pdf (funciona en desarrollo y producción).
    """

    parsed_uri = urlparse(uri)
    uri_path = parsed_uri.path

    # ===== MEDIA =====
    if settings.MEDIA_URL and uri_path.startswith(settings.MEDIA_URL):
        path = os.path.join(
            settings.MEDIA_ROOT,
            uri_path.replace(settings.MEDIA_URL, "").lstrip("/")
        )
        if os.path.isfile(path):
            return path

    # ===== STATIC =====
    if settings.STATIC_URL and uri_path.startswith(settings.STATIC_URL):
        rel_path = uri_path.replace(settings.STATIC_URL, "").lstrip("/")

        # 1️⃣ Desarrollo (STATICFILES_DIRS)
        absolute_path = finders.find(rel_path)
        if absolute_path:
            return absolute_path

        # 2️⃣ Producción (STATIC_ROOT)
        if settings.STATIC_ROOT:
            path = os.path.join(settings.STATIC_ROOT, rel_path)
            if os.path.isfile(path):
                return path

    # ===== RUTA ABSOLUTA =====
    if os.path.isabs(uri_path) and os.path.isfile(uri_path):
        return uri_path

    raise Exception(f'Archivo no encontrado: {uri}')

from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa


def render_to_pdf(template_src, context):
    template = get_template(template_src)
    html = template.render(context)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="detalle_odt.pdf"'

    pisa_status = pisa.CreatePDF(
        html,
        dest=response,
        link_callback=link_callback
    )

    if pisa_status.err:
        return HttpResponse(
            'Error al generar PDF <pre>%s</pre>' % html
        )

    return response

from django.shortcuts import get_object_or_404
from .models import RegistroODT


def odt_detalle_pdf(request, pk):
    odt = get_object_or_404(RegistroODT, pk=pk)

    context = {
        'odt': odt,
        'title': f'Detalle ODT #{odt.pk}',
        'pagesize': 'A4',
    }

    return render_to_pdf(
        'odt/odt_detalle_pdf.html',
        context
    )


from django.shortcuts import render
from django.views.generic import ListView
from django.db.models import Count, Q
from django.db.models.functions import ExtractMonth
from .models import RegistroODT, Maquinaria, TipoMaquinaria, User

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Count, Q

@login_required
@permission_required('controlodt.estadisticas', raise_exception=True)
def reporte_odt_view(request):
    # --- 1. Obtención de filtros desde GET ---
    n_odt = request.GET.get('n_odt')
    maquinaria_id = request.GET.get('maquinaria')
    tipo_id = request.GET.get('tipo_maquinaria')
    prioridad = request.GET.get('prioridad')
    creado_por = request.GET.get('creado_por')
    estado = request.GET.get('estado')
    aprobado_por = request.GET.get('aprobado_por')
    revisado_por = request.GET.get('revisado_por')
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')

    # --- 2. Aplicar Filtros ---
    queryset = RegistroODT.objects.all().order_by('-creado_en')

    if n_odt:
        queryset = queryset.filter(n_odt=n_odt)
    if maquinaria_id:
        queryset = queryset.filter(maquinaria_id=maquinaria_id)
    if tipo_id:
        queryset = queryset.filter(tipo_id=tipo_id)
    if prioridad:
        queryset = queryset.filter(prioridad=prioridad)
    if estado:
        queryset = queryset.filter(estado=estado)
    if creado_por:
        queryset = queryset.filter(
            Q(creado_por__nombre__icontains=creado_por) |
            Q(creado_por__apellido__icontains=creado_por) |
            Q(creado_por__apellidoM__icontains=creado_por)
        )
    if revisado_por:
        queryset = queryset.filter(
            Q(revisado_por__nombre__icontains=revisado_por) |
            Q(revisado_por__apellido__icontains=revisado_por) |
            Q(revisado_por__apellidoM__icontains=revisado_por)
        )
    if aprobado_por:
        queryset = queryset.filter(
            Q(aprobado_por__nombre__icontains=aprobado_por) |
            Q(aprobado_por__apellido__icontains=aprobado_por) |
            Q(aprobado_por__apellidoM__icontains=aprobado_por)
        )
    if fecha_inicio and fecha_fin:
        queryset = queryset.filter(creado_en__range=[fecha_inicio, fecha_fin])

    # --- Totales ---
    total_registros = queryset.count()
    total_aprobadas = queryset.filter(estado=RegistroODT.EstadoODT.CERRADA).count()
    total_revision = queryset.filter(estado=RegistroODT.EstadoODT.EN_EJECUCION).count()
    total_solicitud = queryset.filter(estado=RegistroODT.EstadoODT.SOLICITUD).count()

    # --- 3. Paginación ---
    page = request.GET.get('page', 1)
    paginator = Paginator(queryset, 30)  # 25 registros por página
    
    try:
        odts = paginator.page(page)
    except PageNotAnInteger:
        odts = paginator.page(1)
    except EmptyPage:
        odts = paginator.page(paginator.num_pages)

    # --- 4. Estadísticas para gráficos ---
    # Distribución por estado
    stats_estado_raw = queryset.values('estado').annotate(total=Count('estado')).order_by('-total')
    stats_estado = []
    for item in stats_estado_raw:
        estado_display = dict(RegistroODT.EstadoODT.choices).get(item['estado'], item['estado'])
        porcentaje = (item['total'] / total_registros * 100) if total_registros > 0 else 0
        stats_estado.append({
            'estado': estado_display,
            'total': item['total'],
            'porcentaje': porcentaje
        })

    # Top maquinarias
    stats_maquinaria = queryset.values('maquinaria__nombre').annotate(
        total=Count('maquinaria__nombre')
    ).order_by('-total')
    
    for item in stats_maquinaria:
        item['porcentaje'] = (item['total'] / total_registros * 100) if total_registros > 0 else 0

    # Distribución por tipo
    stats_tipo = queryset.values('tipo__nombre').annotate(
        total=Count('tipo__nombre')
    ).order_by('-total')
    
    for item in stats_tipo:
        item['porcentaje'] = (item['total'] / total_registros * 100) if total_registros > 0 else 0

    # --- 5. Valorización Mensual (Enero a Diciembre) ---
    meses_nombres = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    
    reporte_mensual = []
    for cod_estado, nombre_estado in RegistroODT.EstadoODT.choices:
        conteos_mes = []
        for mes in range(1, 13):
            cantidad = queryset.filter(estado=cod_estado, creado_en__month=mes).count()
            conteos_mes.append(cantidad)
        reporte_mensual.append({
            'estado': nombre_estado,
            'meses': conteos_mes,
            'total_fila': sum(conteos_mes)
        })

    context = {
        'odts': odts,  # Objeto paginado
        'total_registros': total_registros,
        'total_aprobadas': total_aprobadas,
        'total_revision': total_revision,
        'total_solicitud': total_solicitud,
        'stats_estado': stats_estado,
        'stats_tipo': stats_tipo,
        'stats_maquinaria': stats_maquinaria,
        'reporte_mensual': reporte_mensual,
        'meses_cabecera': meses_nombres,
        'filtros': {
            'maquinarias': Maquinaria.objects.all(),
            'tipos': TipoMaquinaria.objects.all(),
            'usuarios': User.objects.all(),
            'estados': RegistroODT.EstadoODT.choices,
            'prioridades': RegistroODT.prioridad_choices,
        }
    }

    return render(request, 'reportes/reporte_odt.html', context)

import base64
from io import BytesIO
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from django.db.models import Count, Q
from datetime import datetime


class PDFStaticResolver:
    def __init__(self, link):
        self.link = link

    def __call__(self, uri, rel):
        if uri.startswith(settings.STATIC_URL):
            path = os.path.join(settings.STATIC_ROOT, uri.replace(settings.STATIC_URL, ""))
        elif uri.startswith(settings.MEDIA_URL):
            path = os.path.join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, ""))
        else:
            return uri
        return path


def generar_grafico_base64(labels, data, title, colors=None):
    """Genera un gráfico de dona y lo retorna como base64"""
    if colors is None:
        colors = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6']
    
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.pie(data, labels=labels, autopct='%1.1f%%', colors=colors[:len(data)], startangle=90)
    ax.set_title(title, fontsize=12, fontweight='bold', pad=20)
    
    buffer = BytesIO()
    plt.tight_layout()
    plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.read()).decode()
    plt.close()
    
    return f"data:image/png;base64,{image_base64}"


def reporte_odt_pdf(request):
    queryset = RegistroODT.objects.all()

    # --- filtros ---
    if request.GET.get('n_odt'):
        queryset = queryset.filter(n_odt=request.GET['n_odt'])

    if request.GET.get('maquinaria'):
        queryset = queryset.filter(maquinaria_id=request.GET['maquinaria'])

    if request.GET.get('tipo_maquinaria'):
        queryset = queryset.filter(tipomaquinaria__tipo_id=request.GET['tipo_maquinaria'])

    if request.GET.get('prioridad'):
        queryset = queryset.filter(prioridad=request.GET['prioridad'])

    if request.GET.get('estado'):
        queryset = queryset.filter(estado=request.GET['estado'])

    if request.GET.get('creado_por'):
        txt = request.GET['creado_por']
        queryset = queryset.filter(
            Q(creado_por__nombre__icontains=txt) |
            Q(creado_por__apellido__icontains=txt) |
            Q(creado_por__apellidoM__icontains=txt)
        )

    if request.GET.get('revisado_por'):
        txt = request.GET['revisado_por']
        queryset = queryset.filter(
            Q(revisado_por__nombre__icontains=txt) |
            Q(revisado_por__apellido__icontains=txt) |
            Q(revisado_por__apellidoM__icontains=txt)
        )

    if request.GET.get('aprobado_por'):
        txt = request.GET['aprobado_por']
        queryset = queryset.filter(
            Q(aprobado_por__nombre__icontains=txt) |
            Q(aprobado_por__apellido__icontains=txt) |
            Q(aprobado_por__apellidoM__icontains=txt)
        )

    # --- totales ---
    total_registros = queryset.count()
    total_aprobadas = queryset.filter(estado=RegistroODT.EstadoODT.CERRADA).count()
    total_revision = queryset.filter(estado=RegistroODT.EstadoODT.EN_EJECUCION).count()
    total_solicitud = queryset.filter(estado=RegistroODT.EstadoODT.SOLICITUD).count()

    # --- Estadísticas para gráficos ---
    # Distribución por estado
    stats_estado = queryset.values('estado').annotate(
        total=Count('id')
    ).order_by('-total')
    
    for item in stats_estado:
        item['estado'] = dict(RegistroODT.EstadoODT.choices).get(item['estado'], item['estado'])
        item['porcentaje'] = (item['total'] / total_registros * 100) if total_registros > 0 else 0

    # Top 5 Maquinarias
    stats_maquinaria = queryset.values('maquinaria__nombre').annotate(
        total=Count('id')
    ).order_by('-total')[:5]

    # Líneas de trabajo (tipos)
    stats_tipo = queryset.values('tipo__nombre').annotate(
        total=Count('id')
    ).order_by('-total')
    
    for item in stats_tipo:
        item['porcentaje'] = (item['total'] / total_registros * 100) if total_registros > 0 else 0

    # --- Generar gráficos como imágenes base64 ---
    grafico_estado = None
    grafico_maquinaria = None
    grafico_tipo = None

    if total_registros > 0:
        # Gráfico de estados
        labels_estado = [item['estado'] for item in stats_estado]
        data_estado = [item['total'] for item in stats_estado]
        grafico_estado = generar_grafico_base64(labels_estado, data_estado, 'Distribución por Estado')

        # Gráfico de maquinarias
        if stats_maquinaria:
            labels_maq = [item['maquinaria__nombre'] for item in stats_maquinaria]
            data_maq = [item['total'] for item in stats_maquinaria]
            grafico_maquinaria = generar_grafico_base64(labels_maq, data_maq, 'Top 5 Maquinarias')

        # Gráfico de tipos
        if stats_tipo:
            labels_tipo = [item['tipo__nombre'] for item in stats_tipo]
            data_tipo = [item['total'] for item in stats_tipo]
            grafico_tipo = generar_grafico_base64(labels_tipo, data_tipo, 'Líneas de Trabajo')

    # --- Tabla de valorización mensual ---
    # Obtener año actual o del filtro
    año_actual = datetime.now().year
    meses_nombres = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    
    # Crear estructura para reporte mensual
    estados_dict = dict(RegistroODT.EstadoODT.choices)
    reporte_mensual = []
    
    for estado_val, estado_nombre in RegistroODT.EstadoODT.choices:
        fila = {
            'estado': estado_nombre,
            'meses': [],
            'total_fila': 0
        }
        
        for mes in range(1, 13):
            count = queryset.filter(
                estado=estado_val,
                fecha_programada__year=año_actual,
                fecha_programada__month=mes
            ).count()
            fila['meses'].append(count)
            fila['total_fila'] += count
        
        reporte_mensual.append(fila)

    context = {
        'odts': queryset,
        'total_registros': total_registros,
        'total_aprobadas': total_aprobadas,
        'total_revision': total_revision,
        'total_solicitud': total_solicitud,
        'grafico_estado': grafico_estado,
        'grafico_maquinaria': grafico_maquinaria,
        'grafico_tipo': grafico_tipo,
        'meses_cabecera': meses_nombres,
        'reporte_mensual': reporte_mensual,
        'año_actual': año_actual,
    }

    template = get_template('reportes/reporte_odt_pdf.html')
    html = template.render(context)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="reporte_odt.pdf"'

    pisa.CreatePDF(
        html,
        dest=response,
        link_callback=PDFStaticResolver(request)
    )
    return response


import openpyxl
from openpyxl.styles import Font, Alignment
from django.http import HttpResponse

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment


def reporte_odt_excel(request):
    queryset = RegistroODT.objects.all()

    # --- filtros ---
    if request.GET.get('n_odt'):
        queryset = queryset.filter(n_odt=request.GET['n_odt'])

    if request.GET.get('maquinaria'):
        queryset = queryset.filter(maquinaria_id=request.GET['maquinaria'])

    if request.GET.get('tipo_maquinaria'):
        queryset = queryset.filter(tipo_id=request.GET['tipo_maquinaria'])

    if request.GET.get('prioridad'):
        queryset = queryset.filter(prioridad=request.GET['prioridad'])

    if request.GET.get('estado'):
        queryset = queryset.filter(estado=request.GET['estado'])

    if request.GET.get('creado_por'):
        txt = request.GET['creado_por']
        queryset = queryset.filter(
            Q(creado_por__nombre__icontains=txt) |
            Q(creado_por__apellido__icontains=txt) |
            Q(creado_por__apellidoM__icontains=txt)
        )

    if request.GET.get('revisado_por'):
        txt = request.GET['revisado_por']
        queryset = queryset.filter(
            Q(revisado_por__nombre__icontains=txt) |
            Q(revisado_por__apellido__icontains=txt) |
            Q(revisado_por__apellidoM__icontains=txt)
        )

    if request.GET.get('aprobado_por'):
        txt = request.GET['aprobado_por']
        queryset = queryset.filter(
            Q(aprobado_por__nombre__icontains=txt) |
            Q(aprobado_por__apellido__icontains=txt) |
            Q(aprobado_por__apellidoM__icontains=txt)
        )

    # --- Crear Excel ---
    wb = Workbook()
    ws = wb.active
    ws.title = "Reporte ODTs"

    # =======================
    # ENCABEZADOS
    # =======================
    headers = [
        "N° ODT",
        "Fecha",
        "Falla Reportada",
        "Línea",
        "Prioridad",
        "Equipo / Parte",
        "Solicitado Por",
        "Entregado A",
        "Estado",
    ]

    ws.append(headers)

    # Estilos encabezados
    for col in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center")

    # =======================
    # CONTENIDO
    # =======================
    for odt in queryset:
        ws.append([
            f"{odt.n_odt:03d}",
            odt.creado_en.strftime("%d/%m/%Y") if odt.creado_en else "",
            odt.titulo,
            getattr(odt.tipo, "nombre", ""),
            odt.get_prioridad_display() if hasattr(odt, "get_prioridad_display") else odt.prioridad,
            getattr(odt.maquinaria, "nombre", ""),
            odt.creado_por.get_full_name() if odt.creado_por else "",
            odt.responsable_ejecucion.get_full_name() if getattr(odt, "responsable_ejecucion", None) else "",
            odt.get_estado_display() if hasattr(odt, "get_estado_display") else odt.estado,
        ])

    # Ajustar ancho
    for column in ws.columns:
        length = max(len(str(cell.value)) for cell in column) + 2
        ws.column_dimensions[column[0].column_letter].width = length

    # --- Respuesta ---
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="reporte_odt.xlsx"'
    wb.save(response)

    return response

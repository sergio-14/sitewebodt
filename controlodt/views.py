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
#@permission_required('dicomar.view_user', raise_exception=True)
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


@login_required
#@permission_required('dicomar.add_user', raise_exception=True)
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
#@permission_required('dicomar.change_user', raise_exception=True)
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
    

from django.db.models import Q

from .models import TipoMaquinaria, Maquinaria
from .forms import TipoMaquinariaForm, MaquinariaForm

# ----- TipoMaquinaria -----
@login_required
#@permission_required('controlodt.view_tipomaquinaria', raise_exception=True)
def tipo_list(request):
    q = request.GET.get('q', '').strip()
    per_page = int(request.GET.get('per_page', 10))
    page = request.GET.get('page', 1)

    qs = TipoMaquinaria.objects.all().order_by('nombre')
    if q:
        qs = qs.filter(nombre__icontains=q)

    paginator = Paginator(qs, per_page)
    page_obj = paginator.get_page(page)

    context = {
        'page_obj': page_obj,
        'q': q,
        'per_page': per_page,
        'per_page_options': [5, 10, 20, 50],
        'total': qs.count(),
    }
    return render(request, 'maquinaria/listar_tipo_maquinaria.html', context)


@login_required
#@permission_required('controlodt.add_tipomaquinaria', raise_exception=True)
def tipo_create(request):
    if request.method == 'POST':
        form = TipoMaquinariaForm(request.POST)
        if form.is_valid():
            obj = form.save()
            messages.success(request, 'Tipo de maquinaria creado.')
            next_url = request.POST.get('next') or reverse('tipo_list')
            return redirect(next_url)
    else:
        form = TipoMaquinariaForm()
    return render(request, 'maquinaria/tipo_maquinaria_form.html', {'form': form, 'title': 'Nuevo Tipo de Maquinaria', 'next_url': request.GET.get('next', reverse('tipo_list'))})


@login_required
#@permission_required('controlodt.change_tipomaquinaria', raise_exception=True)
def tipo_edit(request, pk):
    obj = get_object_or_404(TipoMaquinaria, pk=pk)
    if request.method == 'POST':
        form = TipoMaquinariaForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tipo de maquinaria actualizado.')
            next_url = request.POST.get('next') or reverse('tipo_list')
            return redirect(next_url)
    else:
        form = TipoMaquinariaForm(instance=obj)
    return render(request, 'maquinaria/tipo_maquinaria_form.html', {'form': form, 'title': f'Editar tipo: {obj.nombre}', 'next_url': request.GET.get('next', reverse('tipo_list'))})


# ----- Maquinaria -----
@login_required
#@permission_required('controlodt.view_maquinaria', raise_exception=True)
def maquinaria_list(request):
    q = request.GET.get('q', '').strip()
    tipo = request.GET.get('tipo', '')
    estado = request.GET.get('estado', '')
    per_page = int(request.GET.get('per_page', 10))
    page = request.GET.get('page', 1)

    qs = Maquinaria.objects.select_related('tipo', 'responsable').all().order_by('tipo__nombre', 'nombre')

    if q:
        qs = qs.filter(Q(nombre__icontains=q) | Q(codigo__icontains=q) | Q(descripcion__icontains=q))
    if tipo:
        qs = qs.filter(tipo_id=tipo)
    if estado:
        qs = qs.filter(estado=estado)

    paginator = Paginator(qs, per_page)
    page_obj = paginator.get_page(page)

    tipos = TipoMaquinaria.objects.filter(activo=True).order_by('nombre')

    context = {
        'page_obj': page_obj,
        'q': q,
        'tipo_selected': tipo,
        'estado_selected': estado,
        'tipos': tipos,
        'per_page': per_page,
        'per_page_options': [5, 10, 20, 50],
        'total': qs.count(),
    }
    return render(request, 'maquinaria/listar_maquinaria.html', context)


@login_required
#@permission_required('controlodt.add_maquinaria', raise_exception=True)
def maquinaria_create(request):
    if request.method == 'POST':
        form = MaquinariaForm(request.POST)
        if form.is_valid():
            obj = form.save()
            messages.success(request, 'Maquinaria creada.')
            return redirect(request.POST.get('next') or reverse('maquinaria_list'))
    else:
        form = MaquinariaForm()
    return render(request, 'maquinaria/maquinaria_form.html', {'form': form, 'title': 'Nueva Maquinaria', 'next_url': request.GET.get('next', reverse('maquinaria_list'))})


@login_required
#@permission_required('controlodt.change_maquinaria', raise_exception=True)
def maquinaria_edit(request, pk):
    obj = get_object_or_404(Maquinaria, pk=pk)
    if request.method == 'POST':
        form = MaquinariaForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Maquinaria actualizada.')
            return redirect(request.POST.get('next') or reverse('maquinaria_list'))
    else:
        form = MaquinariaForm(instance=obj)
    return render(request, 'maquinaria/maquinaria_form.html', {'form': form, 'title': f'Editar maquinaria: {obj.nombre}', 'next_url': request.GET.get('next', reverse('maquinaria_list'))})


from django.utils import timezone
from .models import RegistroODT, Maquinaria
from .forms import RegistroODTForm

@login_required
#@permission_required('controlodt.view_registroodt', raise_exception=True)
def odt_list(request):
    q = request.GET.get('q', '').strip()
    estado = request.GET.get('estado', '')
    prioridad = request.GET.get('prioridad', '')
    per_page = int(request.GET.get('per_page', 10))
    page = request.GET.get('page', 1)

    qs = RegistroODT.objects.select_related('maquinaria', 'creado_por','revisado_por', 'aprobado_por').all().order_by('-creado_en')

    if q:
        qs = qs.filter(Q(titulo__icontains=q) | Q(descripcion__icontains=q) | Q(maquinaria__nombre__icontains=q) | Q(maquinaria__codigo__icontains=q))
    if estado:
        qs = qs.filter(estado=estado)
    if prioridad:
        qs = qs.filter(prioridad=prioridad)

    paginator = Paginator(qs, per_page)
    page_obj = paginator.get_page(page)

    context = {
        'page_obj': page_obj,
        'q': q,
        'estado_selected': estado,
        'prioridad_selected': prioridad,
        'per_page': per_page,
        'per_page_options': [5, 10, 20, 50],
        'total': qs.count(),
    }
    return render(request, 'controlodt/listar_odt.html', context)

def user_in_group(user, group_name):
    return user.groups.filter(name=group_name).exists()


@login_required
def odt_create(request):
    if not user_in_group(request.user, 'Operador'): 
        messages.error(request, 'No tienes permisos para crear ODT.')
        return redirect('odt_list')

    if request.method == 'POST':
        form = RegistroODTForm(request.POST, request.FILES)
        if form.is_valid():
            odt = form.save(commit=False)
            odt.creado_por = request.user
            odt.estado = RegistroODT.EstadoODT.REVISION 
           
            odt.save()
            
            messages.success(request, 'ODT creada y enviada a revisión del Supervisor.')
            return redirect(request.POST.get('next') or reverse('odt_list'))
    else:
        form = RegistroODTForm()
        
   
    return render(request, 'controlodt/odt_form.html', {
        'form': form, 
        'title': 'Nuevo Formulario Orden de Trabajo', 
        'next_url': request.GET.get('next', reverse('odt_list'))
    })

@login_required

def odt_edit(request, pk):
    odt = get_object_or_404(RegistroODT, pk=pk)
    if request.method == 'POST':
        form = RegistroODTForm(request.POST, request.FILES, instance=odt)
        if form.is_valid():
            form.save()
            messages.success(request, 'ODT actualizada.')
            return redirect(request.POST.get('next') or reverse('odt_list'))
    else:
        form = RegistroODTForm(instance=odt)
    return render(request, 'controlodt/odt_form.html', {'form': form, 'title': f'Editar ODT #{odt.pk}', 'odt': odt, 'next_url': request.GET.get('next', reverse('odt_list'))})


@login_required

def odt_detail(request, pk):
    odt = get_object_or_404(RegistroODT, pk=pk)
    return render(request, 'controlodt/odt_detail.html', {'odt': odt})


# ---------- ACCIONES DEL FLUJO ----------
@login_required

def odt_request_review(request, pk):
    """Solicitar revisión: cambia estado a REVISION (quien lo pidió queda como creado_por)"""
    odt = get_object_or_404(RegistroODT, pk=pk)
    if request.method == 'POST':
        odt.estado = RegistroODT.EstadoODT.REVISION
        odt.save(update_fields=['estado', 'actualizado_en'])
        messages.success(request, 'ODT marcada para revisión.')
    return redirect(request.POST.get('next') or reverse('odt_list'))


@login_required
def odt_mark_review(request, pk):
    if not user_in_group(request.user, 'Supervisor'):
        messages.error(request, 'No tienes permisos para marcar la ODT como revisada.')
        return redirect('odt_list')

    odt = get_object_or_404(RegistroODT, pk=pk)
    if request.method == 'POST':
        odt.revisado_por = request.user
        odt.save(update_fields=['revisado_por', 'actualizado_en'])
        messages.success(request, 'ODT marcada como revisada.')
    return redirect(request.POST.get('next') or reverse('odt_list'))


@login_required
def odt_approve(request, pk):
    if not user_in_group(request.user, 'Jefe de Área'):
        messages.error(request, 'No tienes permisos para aprobar esta ODT.')
        return redirect('odt_list')

    odt = get_object_or_404(RegistroODT, pk=pk)
    if request.method == 'POST':
        odt.aprobado_por = request.user
        odt.estado = RegistroODT.EstadoODT.APROBADA
        odt.fecha_termino = odt.fecha_termino or timezone.now()
        odt.save(update_fields=['aprobado_por', 'estado', 'fecha_termino', 'actualizado_en'])
        messages.success(request, 'ODT aprobada.')
    return redirect(request.POST.get('next') or reverse('odt_list'))


@login_required
def mis_notificaciones(request):
    user = request.user
    
    is_supervisor = user.groups.filter(name='Supervisor').exists()
    is_jefe_area = user.groups.filter(name='Jefe de Área').exists()

    para_revisar = RegistroODT.objects.none()
    para_aprobar = RegistroODT.objects.none()
    asignadas = RegistroODT.objects.none()

    if is_supervisor:
        para_revisar = RegistroODT.objects.filter(
            estado=RegistroODT.EstadoODT.REVISION,
            revisado_por__isnull=True
        ).order_by('-creado_en')

    if is_jefe_area:
        para_aprobar = RegistroODT.objects.filter(
            estado=RegistroODT.EstadoODT.REVISION,
            revisado_por__isnull=False,  
            aprobado_por__isnull=True
        ).order_by('-creado_en')

  
    if user.groups.filter(name='Operador').exists():
        asignadas = RegistroODT.objects.filter(
           
            estado__in=[RegistroODT.EstadoODT.BORRADOR, RegistroODT.EstadoODT.ASIGNADA]
        ).order_by('-creado_en')

    context = {
        'para_revisar': para_revisar,
        'para_aprobar': para_aprobar,
        'asignadas': asignadas,
        'is_supervisor': is_supervisor, 
        'is_jefe_area': is_jefe_area,   
    }
    return render(request, 'controlodt/mis_notificaciones.html', context)





@login_required
def odt_aprobar_revision(request, pk):
    odt = get_object_or_404(RegistroODT, pk=pk)
    if not request.user.groups.filter(name='Supervisor').exists():
        messages.error(request, "Permiso denegado.")
        return redirect('mis_notificaciones')

    if odt.estado == RegistroODT.EstadoODT.REVISION and odt.revisado_por is None:
        odt.aprobar_revision(request.user) 
        messages.success(request, f"ODT #{odt.pk} revisada y pasada al Jefe de Área.")
    else:
        messages.warning(request, "Esta ODT no está pendiente de su revisión.")
        
    return redirect('mis_notificaciones')

@login_required
def odt_denegar_revision(request, pk):
    odt = get_object_or_404(RegistroODT, pk=pk)
    
    if not request.user.groups.filter(name='Supervisor').exists():
        messages.error(request, "Permiso denegado.")
        return redirect('mis_notificaciones')

    if odt.estado == RegistroODT.EstadoODT.REVISION and odt.revisado_por is None:
        
   
        odt.revisado_por = request.user 
        
       
        odt.estado = RegistroODT.EstadoODT.RECHAZADA
        
        odt.save(update_fields=['estado', 'revisado_por']) 

        messages.error(request, f"ODT #{odt.pk} rechazada. El estado ha cambiado a 'Rechazada'.")
    else:
        messages.warning(request, "Esta ODT no está pendiente de su revisión.")
        
    return redirect('mis_notificaciones')

@login_required
def odt_aprobar(request, pk):
    odt = get_object_or_404(RegistroODT, pk=pk)
  
    if not request.user.groups.filter(name='Jefe de Área').exists():
        messages.error(request, "Permiso denegado.")
        return redirect('mis_notificaciones')

    if odt.estado == RegistroODT.EstadoODT.REVISION and odt.revisado_por is not None and odt.aprobado_por is None:
        
        
        maquina = odt.maquinaria 
        
        maquina.estado = maquina.Estado.EN_MANTENIMIENTO
        maquina.save(update_fields=['estado']) 
        
  
        odt.aprobar_odt(request.user) 
        
        messages.success(request, f"ODT #{odt.pk} aprobada. La maquinaria {maquina.nombre} ha pasado a estado 'En Mantención'.")
    else:
        messages.warning(request, "Esta ODT no está pendiente de su aprobación.")
        
    return redirect('mis_notificaciones')

@login_required
def odt_denegar_aprobacion(request, pk):
    odt = get_object_or_404(RegistroODT, pk=pk)
    if not request.user.groups.filter(name='Jefe de Área').exists():
        messages.error(request, "Permiso denegado.")
        return redirect('mis_notificaciones')

    if odt.estado == RegistroODT.EstadoODT.REVISION and odt.revisado_por is not None and odt.aprobado_por is None:
   
        odt.denegar_aprobacion() 
        
        messages.info(request, f"ODT #{odt.pk} rechazada. El estado ha cambiado a 'Rechazada en Aprobación'.") 
    else:
        messages.warning(request, "Esta ODT no está pendiente de ser rechazada.")
        
    return redirect('mis_notificaciones')


import os
from django.conf import settings
from django.shortcuts import render, get_object_or_404
from django.template.loader import get_template
from django.http import HttpResponse

from xhtml2pdf import pisa 

from .models import RegistroODT 

def link_callback(uri, rel):
    """
    Convierte URI locales (ej. /media/firma.png) a rutas de sistema de archivos.
    """

    if uri.startswith(settings.STATIC_URL):
        path = os.path.join(settings.STATIC_ROOT, uri.replace(settings.STATIC_URL, ""))
    
 
    elif uri.startswith(settings.MEDIA_URL):
        path = os.path.join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, ""))
        
    else:

        return uri
    
 
    if not os.path.isfile(path):
        raise Exception(
            'Ruta de imagen no válida: %s' % path
        )
    return path


def render_to_pdf(template_src, context_dict={}):
    template = get_template(template_src)
    html = template.render(context_dict)
    
    response = HttpResponse(content_type='application/pdf')
    
   
    response['Content-Disposition'] = 'inline; filename="detalle_odt.pdf"'

   
    pisa_status = pisa.CreatePDF(
        html, 
        dest=response, 
  
        link_callback=link_callback 
    )
    
   
    if pisa_status.err:
       
        return HttpResponse('Tuvimos algunos errores al generar el PDF. <pre>' + html + '</pre>')
        
    return response



def odt_detalle_pdf(request, pk):
   
    odt = get_object_or_404(RegistroODT, pk=pk)
    
    context = {
        'odt': odt,
        'title': f'Detalle ODT #{odt.pk}',
        'pagesize': 'A4',
    }
    
    return render_to_pdf('controlodt/odt_detalle_pdf.html', context)
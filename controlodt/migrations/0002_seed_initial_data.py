# controlodt/migrations/0002_seed_initial_data.py
from django.db import migrations, models
from django.utils import timezone
from django.contrib.auth.hashers import make_password


def create_seed_data(apps, schema_editor):
    User = apps.get_model('controlodt', 'User')
    TipoMaquinaria = apps.get_model('controlodt', 'TipoMaquinaria')
    Maquinaria = apps.get_model('controlodt', 'Maquinaria')
    RegistroODT = apps.get_model('controlodt', 'RegistroODT')

    now = timezone.now()

    # -----------------------
    # USERS (5)
    # -----------------------
    users_data = [
        {'email': 'tech1@example.com', 'nombre': 'Carlos', 'apellido': 'Gonzalez'},
        {'email': 'tech2@example.com', 'nombre': 'María', 'apellido': 'Lopez'},
        {'email': 'supervisor@example.com', 'nombre': 'Andrés', 'apellido': 'Perez'},
        {'email': 'approver@example.com', 'nombre': 'Lucia', 'apellido': 'Sanchez'},
        {'email': 'operator@example.com', 'nombre': 'Diego', 'apellido': 'Martinez'},
    ]

    created_users = []
    for u in users_data:
        obj, created = User.objects.get_or_create(
            email=u['email'],
            defaults={
                'nombre': u['nombre'],
                'apellido': u['apellido'],
                'is_active': True,
                'password': make_password('Password123!')
            }
        )
        if not created:
            obj.password = make_password('Password123!')
            obj.save(update_fields=['password'])
        created_users.append(obj)

    # -----------------------
    # TIPOS DE MAQUINARIA (5)
    # -----------------------
    tipos = [
        ('Excavadora', True),
        ('Generador', True),
        ('Bomba', True),
        ('Compresor', True),
        ('Grúa', True),
    ]
    created_tipos = []
    for nombre, activo in tipos:
        t, _ = TipoMaquinaria.objects.get_or_create(nombre=nombre, defaults={'activo': activo})
        created_tipos.append(t)

    # -----------------------
    # MAQUINARIA (5)
    # -----------------------
    # Usar valores literales para 'estado' (no usar Maquinaria.Estado.* dentro de migraciones)
    maquinas_data = [
        {'nombre': 'EX-200', 'codigo': 'M001', 'tipo': created_tipos[0], 'descripcion': 'Excavadora hidráulica 20t', 'estado': 'OPERATIVA'},
        {'nombre': 'GEN-50', 'codigo': 'M002', 'tipo': created_tipos[1], 'descripcion': 'Generador diesel 50kVA', 'estado': 'MANTENIMIENTO'},
        {'nombre': 'BOM-A1', 'codigo': 'M003', 'tipo': created_tipos[2], 'descripcion': 'Bomba centrífuga', 'estado': 'OPERATIVA'},
        {'nombre': 'COMP-7', 'codigo': 'M004', 'tipo': created_tipos[3], 'descripcion': 'Compresor de aire', 'estado': 'FUERA_SERVICIO'},
        {'nombre': 'GRUA-12', 'codigo': 'M005', 'tipo': created_tipos[4], 'descripcion': 'Grúa torre 12t', 'estado': 'OPERATIVA'},
    ]

    created_maquinas = []
    for i, md in enumerate(maquinas_data):
        responsable = created_users[i % len(created_users)]
        m, _ = Maquinaria.objects.get_or_create(
            codigo=md['codigo'],
            defaults={
                'nombre': md['nombre'],
                'tipo_id': md['tipo'].pk,
                'descripcion': md['descripcion'],
                'estado': md['estado'],
                'responsable_id': responsable.pk,
                'activo': True,
            }
        )
        created_maquinas.append(m)

    # -----------------------
    # REGISTRO ODT (5)
    # -----------------------
    # Usar valores literales para 'estado' de ODT también
    odt_data = [
        {
            'maquinaria': created_maquinas[0],
            'titulo': 'Revisión general EX-200',
            'descripcion': 'Revisión preventiva programada.',
            'estado': 'ASIGNADA',
            'prioridad': 'MEDIA',
            'creado_por': created_users[2],
            'asignado_a': created_users[0],
        },
        {
            'maquinaria': created_maquinas[1],
            'titulo': 'Reparación alternador GEN-50',
            'descripcion': 'Alternador presenta fallas eléctricas.',
            'estado': 'EN_EJECUCION',
            'prioridad': 'ALTA',
            'creado_por': created_users[2],
            'asignado_a': created_users[1],
        },
        {
            'maquinaria': created_maquinas[2],
            'titulo': 'Inspección bomba BOM-A1',
            'descripcion': 'Inspección por reducción de caudal.',
            'estado': 'BORRADOR',
            'prioridad': 'BAJA',
            'creado_por': created_users[0],
            'asignado_a': None,
        },
        {
            'maquinaria': created_maquinas[3],
            'titulo': 'Evaluación FUERA_SERVICIO COMP-7',
            'descripcion': 'Evaluar daño y decidir reparación o baja.',
            'estado': 'REVISION',
            'prioridad': 'URGENTE',
            'creado_por': created_users[3],
            'asignado_a': created_users[3],
            'revisado_por': created_users[3],
        },
        {
            'maquinaria': created_maquinas[4],
            'titulo': 'Mantenimiento preventivo GRUA-12',
            'descripcion': 'Cambio de cables y lubricación.',
            'estado': 'APROBADA',
            'prioridad': 'MEDIA',
            'creado_por': created_users[2],
            'asignado_a': created_users[4],
            'revisado_por': created_users[1],
            'aprobado_por': created_users[3],
        },
    ]

    for od in odt_data:
        exists = RegistroODT.objects.filter(titulo=od['titulo'], maquinaria=od['maquinaria']).exists()
        if exists:
            continue
        RegistroODT.objects.create(
            maquinaria_id=od['maquinaria'].pk,
            titulo=od['titulo'],
            descripcion=od['descripcion'],
            estado=od['estado'],
            prioridad=od['prioridad'],
            creado_por_id=od['creado_por'].pk if od.get('creado_por') else None,
            asignado_a_id=od['asignado_a'].pk if od.get('asignado_a') else None,
            revisado_por_id=od.get('revisado_por').pk if od.get('revisado_por') else None,
            aprobado_por_id=od.get('aprobado_por').pk if od.get('aprobado_por') else None,
            fecha_programada=now,
            creado_en=now,
        )


def delete_seed_data(apps, schema_editor):
    User = apps.get_model('controlodt', 'User')
    TipoMaquinaria = apps.get_model('controlodt', 'TipoMaquinaria')
    Maquinaria = apps.get_model('controlodt', 'Maquinaria')
    RegistroODT = apps.get_model('controlodt', 'RegistroODT')

    odt_titles = [
        'Revisión general EX-200',
        'Reparación alternador GEN-50',
        'Inspección bomba BOM-A1',
        'Evaluación FUERA_SERVICIO COMP-7',
        'Mantenimiento preventivo GRUA-12',
    ]
    RegistroODT.objects.filter(titulo__in=odt_titles).delete()

    codigos = ['M001', 'M002', 'M003', 'M004', 'M005']
    Maquinaria.objects.filter(codigo__in=codigos).delete()

    tipo_nombres = ['Excavadora', 'Generador', 'Bomba', 'Compresor', 'Grúa']
    TipoMaquinaria.objects.filter(nombre__in=tipo_nombres).delete()

    user_emails = ['tech1@example.com', 'tech2@example.com', 'supervisor@example.com', 'approver@example.com', 'operator@example.com']
    User.objects.filter(email__in=user_emails).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('controlodt', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_seed_data, delete_seed_data),
    ]

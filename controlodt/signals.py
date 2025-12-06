from django.db.models import Q
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from .models import Maquinaria, RegistroODT

@receiver(pre_save, sender=Maquinaria)
def _maquinaria_pre_save(sender, instance: Maquinaria, **kwargs):
    if instance.pk:
        try:
            previous = Maquinaria.objects.get(pk=instance.pk)
            instance._previous_estado = previous.estado
        except Maquinaria.DoesNotExist:
            instance._previous_estado = None
    else:
        instance._previous_estado = None


@receiver(post_save, sender=Maquinaria)
def _maquinaria_post_save(sender, instance: Maquinaria, created, **kwargs):
    """
    Si el estado cambia a MANTENIMIENTO o FUERA_SERVICIO, crea una ODT
    automática (si no existe ya una abierta similar).
    """
    prev = getattr(instance, '_previous_estado', None)
    if instance.needs_ot_creation(prev):
     
        window = timezone.now() - timezone.timedelta(days=7)  
        existe = RegistroODT.objects.filter(
            maquinaria=instance,
            estado__in=[
                RegistroODT.EstadoODT.BORRADOR,
                RegistroODT.EstadoODT.ASIGNADA,
                RegistroODT.EstadoODT.EN_EJECUCION,
                RegistroODT.EstadoODT.REVISION
            ],
            creado_en__gte=window
        ).exists()
        if not existe:
          
            RegistroODT.objects.create(
                maquinaria=instance,
                titulo=f'Intervención por cambio de estado: {instance.get_estado_display()}',
                descripcion=f'ODT generada automáticamente por cambio de estado de la maquinaria {instance} a {instance.get_estado_display()}.',
                estado=RegistroODT.EstadoODT.BORRADOR,
                prioridad='MEDIA',
                creado_por=instance.responsable if instance.responsable else None,
            )

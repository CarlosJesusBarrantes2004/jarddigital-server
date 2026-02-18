from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.users.models import Usuario
from apps.sales.models import GrabadorAudio

@receiver(post_save, sender=Usuario)
def gestionar_grabador_automatico(sender, instance, created, **kwargs):
    """
    Cada vez que se crea o edita un Usuario, verificamos si debe ser un Grabador.
    Regla: Todos son grabadores EXCEPTO los de rol BACKOFFICE.
    """
    if not instance.id_rol:
        return

    # Si el rol es BACKOFFICE, no debe estar en la tabla (o lo borramos si existía)
    if instance.id_rol.codigo == 'BACKOFFICE':
        GrabadorAudio.objects.filter(id_usuario=instance).delete()
    else:
        # Si tiene cualquier otro rol (ASESOR, SUPERVISOR, DUENO), lo sincronizamos
        # update_or_create: Si existe lo actualiza, si no, lo crea.
        GrabadorAudio.objects.update_or_create(
            id_usuario=instance,
            defaults={
                'nombre_completo': instance.nombre_completo,
                'activo': instance.activo
            }
        )
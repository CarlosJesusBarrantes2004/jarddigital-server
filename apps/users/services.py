from django.db import transaction
from .models import Usuario, PermisoAcceso
# Importamos el modelo de GrabadorAudio
from apps.sales.models import GrabadorAudio

def _sincronizar_grabador(usuario: Usuario):
    """
    Función auxiliar privada para centralizar la regla de negocio:
    Todos son grabadores EXCEPTO los de rol BACKOFFICE.
    """
    if not usuario.id_rol:
        return

    if usuario.id_rol.codigo == 'BACKOFFICE':
        GrabadorAudio.objects.filter(id_usuario=usuario).delete()
    else:
        GrabadorAudio.objects.update_or_create(
            id_usuario=usuario,
            defaults={
                'nombre_completo': usuario.nombre_completo,
                'activo': usuario.activo
            }
        )

def crear_usuario_admin(*, datos_validados: dict) -> Usuario:
    ids_sedes = datos_validados.pop('ids_modalidades_sede', [])
    password = datos_validados.pop('password', None)

    with transaction.atomic():
        usuario = Usuario(**datos_validados)
        if password:
            usuario.set_password(password)
        usuario.save()

        if ids_sedes:
            permisos = [PermisoAcceso(id_usuario=usuario, id_modalidad_sede_id=mod_id) for mod_id in ids_sedes]
            PermisoAcceso.objects.bulk_create(permisos)

        # ---> INYECCIÓN DE LÓGICA: Sincronizamos el grabador explícitamente <---
        _sincronizar_grabador(usuario)

    return usuario


def actualizar_usuario_admin(*, usuario: Usuario, datos_validados: dict) -> Usuario:
    ids_sedes = datos_validados.pop('ids_modalidades_sede', None)
    password = datos_validados.pop('password', None)

    with transaction.atomic():
        for attr, value in datos_validados.items():
            setattr(usuario, attr, value)

        if password:
            usuario.set_password(password)

        usuario.save()

        if ids_sedes is not None:
            PermisoAcceso.objects.filter(id_usuario=usuario).delete()
            if ids_sedes:
                permisos = [PermisoAcceso(id_usuario=usuario, id_modalidad_sede_id=mod_id) for mod_id in ids_sedes]
                PermisoAcceso.objects.bulk_create(permisos)

        # ---> INYECCIÓN DE LÓGICA: Sincronizamos el grabador explícitamente <---
        _sincronizar_grabador(usuario)

    return usuario
from django.db import transaction
from .models import Usuario, PermisoAcceso

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

    return usuario
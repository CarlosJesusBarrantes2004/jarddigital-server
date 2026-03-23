from django.db.models import QuerySet
from .models import Usuario

def obtener_usuarios_permitidos(usuario_peticion, queryset_base: QuerySet) -> QuerySet:
    """
    Aplica Row-Level Security: Filtra el universo de usuarios
    dependiendo de quién está haciendo la petición.
    """
    # Si no tiene rol (por si acaso), devolvemos el queryset intacto
    if not (hasattr(usuario_peticion, 'id_rol') and usuario_peticion.id_rol):
        return queryset_base

    # Si es SUPERVISOR, creamos su "universo cerrado" de datos
    if usuario_peticion.id_rol.codigo == 'SUPERVISOR':
        sedes_supervisor_ids = usuario_peticion.asignaciones_supervisor.filter(
            activo=True,
            fecha_fin__isnull=True
        ).values_list('id_modalidad_sede', flat=True)

        return queryset_base.filter(
            id_rol__codigo='ASESOR',
            permisos__id_modalidad_sede__in=sedes_supervisor_ids
        ).distinct()

    # Si es DUEÑO o ADMIN, ve todo el queryset base
    return queryset_base
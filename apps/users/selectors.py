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


def extraer_contexto_modalidad_sede(usuario: Usuario) -> dict:
    """
    Helper centralizado para extraer la Sucursal (Sede) y la Modalidad de un asesor.
    Soporta eficientemente:
      1. Custom Prefetch (to_attr='permisos_activos_prefetched')
      2. Prefetch relacional estándar de Django (_prefetched_objects_cache)
      3. Consultas individuales directas en vivo (Fallback seguro con select_related)
    """
    contexto = {
        "sede_nombre": "SIN SEDE",
        "modalidad_codigo": "",
        "texto_completo": "SIN MODALIDAD/SEDE"
    }

    if not usuario:
        return contexto

    permiso = None

    # Caso 1: Viene del lote masivo de planillas (Atributo virtual custom)
    if hasattr(usuario, 'permisos_activos_prefetched'):
        if usuario.permisos_activos_prefetched:
            permiso = usuario.permisos_activos_prefetched[0]

    # Caso 2: Viene del lote de Tracking o consultas con prefetch_related estándar
    else:
        permisos_qs = usuario.permisos.all()

        # Si NO está pre-cargado en la caché de Django, optimizamos la consulta individual
        # para evitar consultas N+1 aisladas en los endpoints individuales.
        if not (hasattr(usuario, '_prefetched_objects_cache') and 'permisos' in usuario._prefetched_objects_cache):
            permisos_qs = permisos_qs.select_related(
                'id_modalidad_sede__id_sucursal',
                'id_modalidad_sede__id_modalidad'
            )

        permiso = permisos_qs.first()

    # Extracción de datos con la cadena exacta de relaciones indicadas
    if permiso and permiso.id_modalidad_sede:
        mod_sede = permiso.id_modalidad_sede

        if getattr(mod_sede, 'id_sucursal', None):
            contexto["sede_nombre"] = mod_sede.id_sucursal.nombre

        if getattr(mod_sede, 'id_modalidad', None):
            contexto["modalidad_codigo"] = mod_sede.id_modalidad.codigo

        # Construcción del texto plano combinado
        if contexto["modalidad_codigo"]:
            contexto["texto_completo"] = f"{contexto['sede_nombre']} - {contexto['modalidad_codigo']}"
        else:
            contexto["texto_completo"] = contexto["sede_nombre"]

    return contexto
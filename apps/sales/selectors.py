from django.utils import timezone
from django.db.models import QuerySet, Prefetch, Exists, OuterRef, Q
from apps.users.models import PermisoAcceso
from .models import Venta


def obtener_grabadores_disponibles(queryset_base: QuerySet, id_venta_actual: int = None) -> QuerySet:
    """
    Filtra el queryset de GrabadorAudio para devolver solo los disponibles hoy.
    Si se está editando una venta (id_venta_actual), se le da un 'Pase VIP' al grabador de esa venta.
    """
    hoy = timezone.localdate()

    # 1. Buscamos los ocupados hoy
    ids_bloqueados = Venta.objects.filter(
        fecha_creacion__date=hoy,
        activo=True
    ).exclude(
        id_grabador_audios=1
    ).values_list('id_grabador_audios', flat=True)

    # Convertimos a un Set mutable para poder manipular la lista
    ids_bloqueados = set(ids_bloqueados)

    # ---> LA MAGIA DEL PASE VIP <---
    # 2. Si el frontend nos avisa que está editando una venta específica...
    if id_venta_actual:
        venta_actual = Venta.objects.filter(id=id_venta_actual).first()
        if venta_actual and venta_actual.id_grabador_audios:
            grabador_actual_id = venta_actual.id_grabador_audios.id

            # Si el dueño está en la lista negra, lo sacamos para que SÍ aparezca en el dropdown
            if grabador_actual_id in ids_bloqueados:
                ids_bloqueados.remove(grabador_actual_id)

    if ids_bloqueados:
        return queryset_base.exclude(id__in=ids_bloqueados)

    return queryset_base


def aplicar_rls_ventas(queryset: QuerySet, usuario_peticion) -> QuerySet:
    """
    Módulo puro de Seguridad: Solo filtra QUÉ filas puede ver el usuario.
    No hace joins ni carga memoria.
    """
    if not (hasattr(usuario_peticion, 'id_rol') and usuario_peticion.id_rol):
        return queryset

    codigo_rol = usuario_peticion.id_rol.codigo.upper()

    if codigo_rol in ['COORDINADOR', 'DUENO']:
        return queryset

    if codigo_rol == 'ASESOR':
        return queryset.filter(id_asesor=usuario_peticion)

    elif codigo_rol == 'SUPERVISOR':
        sedes_supervisadas = usuario_peticion.asignaciones_supervisor.filter(
            activo=True, fecha_fin__isnull=True
        ).values_list('id_modalidad_sede', flat=True)

        return queryset.filter(
            Q(id_origen_venta__in=sedes_supervisadas) |
            Q(id_supervisor_vigente__id_supervisor=usuario_peticion)
        ).distinct()

    elif codigo_rol in ['BACKOFFICE', 'SEGUIMIENTO']:
        sedes_asignadas = PermisoAcceso.objects.filter(
            id_usuario=usuario_peticion, id_modalidad_sede__activo=True
        ).values_list('id_modalidad_sede', flat=True)

        qs_filtrado = queryset.filter(id_origen_venta__in=sedes_asignadas)

        # Regla extra estricta para SEGUIMIENTO
        if codigo_rol == 'SEGUIMIENTO':
            qs_filtrado = qs_filtrado.filter(id_estado_sot__codigo__iexact='ATENDIDO')

        return qs_filtrado

    return queryset


def obtener_ventas_permitidas(usuario_peticion) -> QuerySet:
    """
    Selector original de Ventas: Aplica RLS y carga TODO (incluyendo audios).
    """
    # 1. Aplicamos la seguridad primero
    queryset = aplicar_rls_ventas(Venta.objects.filter(activo=True), usuario_peticion)

    # 2. Optimizamos para el módulo de Ventas (El monstruo completo)
    reingresos_activos = Venta.objects.filter(venta_origen=OuterRef('pk'), activo=True)

    return queryset.select_related(
        'id_asesor', 'id_producto', 'id_estado_sot', 'id_sub_estado_sot',
        'id_estado_audios', 'id_tipo_documento', 'venta_origen'
    ).prefetch_related(
        'id_origen_venta__id_sucursal', 'id_origen_venta__id_modalidad',
        'id_supervisor_vigente__id_supervisor',
        'id_distrito_nacimiento__id_provincia__id_departamento',
        'id_distrito_instalacion__id_provincia__id_departamento',
        'id_grabador_audios', 'usuario_revision_audios',
        'audios'  # <--- Aquí sí cargamos los audios
    ).annotate(
        _ya_reingresada=Exists(reingresos_activos)
    )
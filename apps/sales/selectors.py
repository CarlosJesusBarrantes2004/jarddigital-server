from django.utils import timezone
from django.db.models import QuerySet, Exists, OuterRef, Q
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


def obtener_ventas_permitidas(usuario_peticion) -> QuerySet:
    """
    Retorna el QuerySet base optimizado (con select_related),
    con anotaciones para evitar N+1, y filtrado por RLS.
    """
    # OuterRef('pk') hace referencia al ID de la Venta principal que se está consultando
    reingresos_activos = Venta.objects.filter(
        venta_origen=OuterRef('pk'),
        activo=True
    )

    # ---> Balanceo de Carga entre SQL y Python <---
    queryset = Venta.objects.select_related(
        # 1. Select Related: SOLO relaciones directas (1 salto) vitales para pintar la tabla
        'id_asesor',
        'id_producto',
        'id_estado_sot',
        'id_sub_estado_sot',
        'id_estado_audios',
        'id_tipo_documento',
        'venta_origen'
    ).prefetch_related(
        # 2. Prefetch Related: Relaciones profundas (2+ saltos) y Múltiples
        'id_origen_venta__id_sucursal',
        'id_origen_venta__id_modalidad',
        'id_supervisor_vigente__id_supervisor',
        'id_distrito_nacimiento__id_provincia__id_departamento',
        'id_distrito_instalacion__id_provincia__id_departamento',
        'id_grabador_audios',
        'usuario_revision_audios',
        'audios'
    ).annotate(
        # 3. Anotaciones
        _ya_reingresada=Exists(reingresos_activos)
    ).all()

    # 2. Seguridad de Datos (Tenant Isolation)
    if not (hasattr(usuario_peticion, 'id_rol') and usuario_peticion.id_rol):
        return queryset

    codigo_rol = usuario_peticion.id_rol.codigo.upper()

    if codigo_rol in ['COORDINADOR', 'DUENO']:
        return queryset

    if codigo_rol == 'ASESOR':
        return queryset.filter(id_asesor=usuario_peticion)
    elif codigo_rol == 'SUPERVISOR':
        # 1. Buscamos las sedes que supervisa HOY
        sedes_supervisadas = usuario_peticion.asignaciones_supervisor.filter(
            activo=True, fecha_fin__isnull=True
        ).values_list('id_modalidad_sede', flat=True)

        # 2. El Filtro Híbrido (OR)
        return queryset.filter(
            Q(id_origen_venta__in=sedes_supervisadas) |  # Puerta Operativa (Lo que maneja hoy)
            Q(id_supervisor_vigente__id_supervisor=usuario_peticion)  # Puerta Histórica (Su sello personal)
        ).distinct()  # Ponemos distinct() por si acaso alguna venta coincide en ambas reglas
    elif codigo_rol == 'BACKOFFICE':
        sedes_asignadas = PermisoAcceso.objects.filter(
            id_usuario=usuario_peticion, id_modalidad_sede__activo=True
        ).values_list('id_modalidad_sede', flat=True)
        return queryset.filter(id_origen_venta__in=sedes_asignadas)
    elif codigo_rol == 'SEGUIMIENTO':
        # 1. Buscamos sus sedes asignadas (Igual que Backoffice)
        sedes_asignadas = PermisoAcceso.objects.filter(
            id_usuario=usuario_peticion, id_modalidad_sede__activo=True
        ).values_list('id_modalidad_sede', flat=True)

        # 2. Retornamos SOLO las ventas de sus sedes Y que estén ATENDIDAS
        # (Usamos iexact para curarnos en salud si en la BD dice "Atendido" o "ATENDIDO")
        return queryset.filter(
            id_origen_venta__in=sedes_asignadas,
            id_estado_sot__codigo__iexact='ATENDIDO'
        )

    return queryset
from django.utils import timezone
from django.db.models import QuerySet, Count, Exists, OuterRef, Q, F
from django.db.models.functions import ExtractMonth
from apps.users.models import PermisoAcceso
from .models import Venta
from datetime import date


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
        'audios', # <--- Aquí sí cargamos los audios
        'seguimiento__meses_evaluados'
    ).annotate(
        _ya_reingresada=Exists(reingresos_activos)
    )



def obtener_metricas_asesor(*, usuario, anio: int) -> dict:
    """
    Extrae las métricas personales de un asesor.
    Incluye desglose mensual, recuento anual, Top de Productos y
    una proyección motivacional (Month-to-Date) comparando con el mes anterior.

    NOTA IMPORTANTE: 'fecha_real_inst' es null hasta que la venta se atiende.
    Por eso usamos DOS querysets base distintos:
      - queryset_atendidas: filtra por fecha_real_inst (instalación) → ATENDIDAS/PAGADAS
      - queryset_pendientes: filtra por fecha_venta (registro) → PENDIENTES
    Mezclar ambos en un solo queryset_base haría que 'total_pendientes'
    siempre devuelva 0, porque las pendientes no tienen fecha_real_inst.
    """

    # ============================================================
    # QUERYSETS BASE SEPARADOS POR LA RAZÓN DOCUMENTADA ARRIBA
    # ============================================================
    queryset_atendidas = Venta.objects.filter(
        id_asesor=usuario,
        fecha_real_inst__year=anio,
        activo=True
    )

    queryset_pendientes = Venta.objects.filter(
        id_asesor=usuario,
        fecha_venta__year=anio,
        id_estado_sot__codigo__iexact='PENDIENTE',
        activo=True
    )

    # Filtros seguros Anti Fan-Out
    filtro_atendidas = Q(id_estado_sot__codigo__iexact='ATENDIDO')

    # mes_numero=1 garantiza unicidad por seguimiento (solo existe 1 registro
    # con mes_numero=1 por seguimiento), por eso distinct=True en el Count
    # es suficiente para evitar inflar el conteo aquí.
    filtro_pagadas = Q(
        id_estado_sot__codigo__iexact='ATENDIDO',
        seguimiento__meses_evaluados__mes_numero=1,
        seguimiento__meses_evaluados__pago_cliente_realizado=True
    )

    # ============================================================
    # 1. AGRUPACIÓN MENSUAL — ATENDIDAS Y PAGADAS (por fecha de instalación)
    # ============================================================
    ventas_por_mes = list(
        queryset_atendidas.annotate(
            mes=ExtractMonth('fecha_real_inst')
        ).values('mes').annotate(
            total_atendidas=Count('id', filter=filtro_atendidas, distinct=True),
            total_pagadas=Count('id', filter=filtro_pagadas, distinct=True)
        ).order_by('mes')
    )

    # ============================================================
    # 1b. AGRUPACIÓN MENSUAL — PENDIENTES (por fecha de venta)
    # ============================================================
    pendientes_por_mes = list(
        queryset_pendientes.annotate(
            mes=ExtractMonth('fecha_venta')
        ).values('mes').annotate(
            total_pendientes=Count('id', distinct=True)
        ).order_by('mes')
    )

    # ============================================================
    # FUSIÓN DE AMBOS DESGLOSES EN UN SOLO MAPA POR MES (1 al 12)
    # ============================================================
    mapa_meses = {
        m: {"mes": m, "total_atendidas": 0, "total_pagadas": 0, "total_pendientes": 0}
        for m in range(1, 13)
    }

    for fila in ventas_por_mes:
        mapa_meses[fila['mes']]['total_atendidas'] = fila['total_atendidas']
        mapa_meses[fila['mes']]['total_pagadas'] = fila['total_pagadas']

    for fila in pendientes_por_mes:
        mapa_meses[fila['mes']]['total_pendientes'] = fila['total_pendientes']

    desglose_mensual = list(mapa_meses.values())

    # ============================================================
    # 2. RECUENTO GLOBAL DEL AÑO
    # ============================================================
    totales_anio = queryset_atendidas.aggregate(
        gran_total_atendidas=Count('id', filter=filtro_atendidas, distinct=True),
        gran_total_pagadas=Count('id', filter=filtro_pagadas, distinct=True)
    )
    totales_anio['gran_total_pendientes'] = queryset_pendientes.count()

    for key in totales_anio:
        if totales_anio[key] is None:
            totales_anio[key] = 0

    # ============================================================
    # 🌟 EL TOQUE EXTRA 1: TOP 5 PRODUCTOS MÁS VENDIDOS (atendidas)
    # ============================================================
    top_productos = list(
        queryset_atendidas.filter(id_estado_sot__codigo__iexact='ATENDIDO')
        .values(nombre=F('id_producto__nombre_paquete'))
        .annotate(total=Count('id', distinct=True))
        .order_by('-total')[:5]
    )

    # ============================================================
    # 🌟 EL TOQUE EXTRA 2: PROYECCIÓN MTD (Month-To-Date)
    # ============================================================
    hoy = date.today()
    proyeccion = None

    # Solo calculamos proyección si están consultando el año en curso
    if anio == hoy.year:
        mes_actual = hoy.month
        dia_actual = hoy.day

        # Matemáticas para obtener el mes anterior (manejando enero -> diciembre)
        if mes_actual == 1:
            mes_anterior = 12
            anio_anterior = hoy.year - 1
        else:
            mes_anterior = mes_actual - 1
            anio_anterior = hoy.year

        # Ventas del mes actual hasta el día de hoy
        ventas_actuales = Venta.objects.filter(
            id_asesor=usuario, activo=True, id_estado_sot__codigo__iexact='ATENDIDO',
            fecha_real_inst__year=hoy.year, fecha_real_inst__month=mes_actual,
            fecha_real_inst__day__lte=dia_actual
        ).count()

        # Ventas del mes pasado hasta el mismo día de corte
        ventas_pasadas = Venta.objects.filter(
            id_asesor=usuario, activo=True, id_estado_sot__codigo__iexact='ATENDIDO',
            fecha_real_inst__year=anio_anterior, fecha_real_inst__month=mes_anterior,
            fecha_real_inst__day__lte=dia_actual
        ).count()

        tendencia = "IGUAL"
        porcentaje = 0
        if ventas_pasadas > 0:
            crecimiento = ((ventas_actuales - ventas_pasadas) / ventas_pasadas) * 100
            tendencia = "MEJOR" if crecimiento > 0 else ("PEOR" if crecimiento < 0 else "IGUAL")
            porcentaje = abs(round(crecimiento))
        elif ventas_actuales > 0:
            tendencia = "MEJOR"
            porcentaje = 100

        proyeccion = {
            "ventas_mes_actual_hasta_hoy": ventas_actuales,
            "ventas_mes_anterior_hasta_hoy": ventas_pasadas,
            "tendencia": tendencia,
            "porcentaje": porcentaje,
            "mensaje": f"Llevas {ventas_actuales} ventas. El mes pasado a esta fecha llevabas {ventas_pasadas}."
        }

    return {
        "anio_evaluado": anio,
        "asesor": usuario.nombre_completo,
        "totales_anio": totales_anio,
        "desglose_mensual": desglose_mensual,
        "top_productos": top_productos,
        "proyeccion_motivacional": proyeccion
    }
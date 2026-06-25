from django.db.models import Count, Sum, Case, When, IntegerField, F, Q, Prefetch
from django.db.models.functions import ExtractMonth, TruncDay

from apps.sales.models import Venta
from apps.users.models import Usuario, PermisoAcceso
from apps.users.selectors import extraer_contexto_modalidad_sede


# ==========================================
# HELPER INTERNO: Generador de anotaciones mensuales
# ==========================================
def _anotaciones_meses(campo_fecha: str) -> dict:
    """
    Genera dinámicamente las 12 anotaciones Sum(Case(...)) para evitar
    repetir 12 líneas casi idénticas y el riesgo de error de transcripción.
    """
    return {
        f"m{mes}": Sum(
            Case(
                When(**{f"{campo_fecha}__month": mes}, then=1),
                default=0,
                output_field=IntegerField()
            )
        )
        for mes in range(1, 13)
    }


# ==========================================
# SELECTOR BASE COMPARTIDO
# ==========================================
def query_base_ventas_filtradas(
    *,
    anio: int,
    estado_sot: str = None,
    modalidad: str = None,
    campo_fecha: str = 'fecha_real_inst'
):
    """
    Selector base con los filtros globales aplicados.
    NO TOCA la relación 'permisos' aquí — eso se resuelve en un paso aparte
    para evitar fan-out (duplicación de filas por JOIN uno-a-muchos).
    """
    filtros = {f"{campo_fecha}__year": anio, "activo": True}
    queryset = Venta.objects.filter(**filtros)

    if estado_sot:
        # estado_sot es una FK (id_estado_sot), se filtra por su código
        queryset = queryset.filter(id_estado_sot__codigo__iexact=estado_sot)

    if modalidad:
        # Aquí SÍ es seguro filtrar (no traer datos) por modalidad,
        # porque filter() no causa fan-out — solo afecta el WHERE, no el SELECT.
        # .distinct() es obligatorio porque el JOIN puede emparejar de más filas
        # candidatas antes de filtrar, aunque el resultado final sea el mismo set de ventas.
        queryset = queryset.filter(
            id_asesor__permisos__id_modalidad_sede__id_modalidad__codigo__iexact=modalidad
        ).distinct()

    return queryset


# ==========================================
# RESOLUCIÓN DE SEDE/MODALIDAD EN PASO SEPARADO (sin fan-out)
# ==========================================
def _resolver_sedes_modalidades(ids_asesores: list[int]) -> dict:
    """
    Dado un listado de IDs de asesores, devuelve un diccionario
    {id_asesor: "Sede Norte - CALL"} usando el helper centralizado.

    Se hace en UNA sola consulta batch con prefetch, nunca un loop con
    queries individuales.
    """
    asesores = Usuario.objects.filter(id__in=ids_asesores).prefetch_related(
        Prefetch(
            'permisos',
            queryset=PermisoAcceso.objects.select_related(
                'id_modalidad_sede__id_modalidad',
                'id_modalidad_sede__id_sucursal'
            ),
            to_attr='permisos_activos_prefetched'
        )
    )

    resultado = {}
    for asesor in asesores:
        contexto = extraer_contexto_modalidad_sede(asesor)
        resultado[asesor.id] = {
            "sede": contexto["sede_nombre"],
            "modalidad": contexto["modalidad_codigo"],
            "sede_modalidad": contexto["texto_completo"]
        }
    return resultado


# ==========================================
# GRÁFICOS 1 y 3 — MATRIZ PIVOTE (Asesor x Mes, con totales)
# ==========================================
def obtener_matriz_pivote_sql(*, anio: int, estado_sot: str) -> dict:
    """
    Resuelve los Gráficos 1 y 3 calculando celdas y totales de fila/columna
    directamente en SQL. La sede/modalidad se resuelve en un segundo paso
    (sin fan-out) y se inyecta en memoria sobre el resultado ya agregado.
    """
    queryset = query_base_ventas_filtradas(anio=anio, estado_sot=estado_sot)

    anotaciones = _anotaciones_meses('fecha_real_inst')

    # 1. Filas de la matriz con su total de fila (horizontal) — SIN tocar permisos aquí
    filas_matriz = list(
        queryset.values(
            asesor_id=F('id_asesor__id'),
            asesor_nombre=F('id_asesor__nombre_completo'),
        ).annotate(
            **anotaciones,
            total_asesor=Count('id')
        ).order_by('asesor_nombre')
    )

    # 2. Totales de columna (vertical) + esquina inferior derecha — 1 sola query aggregate
    totales_columnas = queryset.aggregate(
        **anotaciones,
        grand_total=Count('id')
    )

    # 3. Resolver sede/modalidad en batch para todos los asesores que aparecieron
    ids_asesores = [fila['asesor_id'] for fila in filas_matriz]
    mapa_sedes = _resolver_sedes_modalidades(ids_asesores)

    # 4. Inyectar sede/modalidad en cada fila (en memoria, ya sin riesgo de fan-out)
    for fila in filas_matriz:
        info_sede = mapa_sedes.get(fila['asesor_id'], {"sede_modalidad": "SIN SEDE"})
        fila['sede_modalidad'] = info_sede['sede_modalidad']

    # Reordenar por sede_modalidad ahora que ya la tenemos (no se puede hacer en SQL aquí)
    filas_matriz.sort(key=lambda f: (f['sede_modalidad'], f['asesor_nombre']))

    return {
        "filas": filas_matriz,
        "totales_columnas": totales_columnas
    }


# ==========================================
# GRÁFICOS 2 y 4 — BARRAS DE RENDIMIENTO
# ==========================================
def query_barras_rendimiento(*, anio: int, estado_sot: str = None, mes: int = None, id_asesor: int = None) -> list:
    """
    Resuelve los Gráficos 2 y 4. Misma estrategia: agregamos por asesor
    primero, resolvemos sede/modalidad después.
    """
    queryset = query_base_ventas_filtradas(anio=anio, estado_sot=estado_sot)

    if id_asesor:
        queryset = queryset.filter(id_asesor_id=id_asesor)

    if mes:
        # Gráfico 2: Un mes específico, agrupado por asesor
        queryset = queryset.filter(fecha_real_inst__month=mes)
        filas = list(
            queryset.values(
                asesor_id=F('id_asesor__id'),
                asesor_nombre=F('id_asesor__nombre_completo'),
            ).annotate(total_ventas=Count('id')).order_by('-total_ventas')
        )
    else:
        # Gráfico 4: Evolución mensual, agrupado por asesor y mes
        filas = list(
            queryset.annotate(
                num_mes=ExtractMonth('fecha_real_inst')
            ).values(
                'num_mes',
                asesor_id=F('id_asesor__id'),
                asesor_nombre=F('id_asesor__nombre_completo'),
            ).annotate(total_ventas=Count('id')).order_by('num_mes', 'asesor_nombre')
        )

    # Resolver sede/modalidad en batch y enriquecer las filas
    ids_asesores = list({fila['asesor_id'] for fila in filas})
    mapa_sedes = _resolver_sedes_modalidades(ids_asesores)

    for fila in filas:
        info_sede = mapa_sedes.get(fila['asesor_id'], {"sede_modalidad": "SIN SEDE"})
        fila['sede_modalidad'] = info_sede['sede_modalidad']

    return filas


# ==========================================
# GRÁFICO 5 — TENDENCIA DIARIA (Líneas comparativas)
# ==========================================
def obtener_tendencia_diaria(*, anio: int, mes: int, modalidad: str = None) -> dict:
    """
    Resuelve el Gráfico 5: serie día-a-día de un mes específico, con total final.
    Se llama dos veces desde el frontend (una por cada mes a comparar).
    """
    queryset = Venta.objects.filter(
        id_estado_sot__codigo__iexact='ATENDIDO',
        fecha_real_inst__year=anio,
        fecha_real_inst__month=mes,
        activo=True
    )

    if modalidad:
        # filter() puro, no values() con el campo incluido → sin riesgo de fan-out
        queryset = queryset.filter(
            id_asesor__permisos__id_modalidad_sede__id_modalidad__codigo__iexact=modalidad
        ).distinct()

    serie = list(
        queryset.annotate(
            dia=TruncDay('fecha_real_inst')
        ).values('dia').annotate(
            total=Count('id')
        ).order_by('dia')
    )

    total_mes = sum(item['total'] for item in serie)

    return {
        "anio": anio,
        "mes": mes,
        "modalidad": modalidad or "TODAS",
        "serie": [
            {"fecha": item['dia'].strftime('%Y-%m-%d'), "total": item['total']}
            for item in serie
        ],
        "total_mes": total_mes
    }


# ==========================================
# GRÁFICO 6 — ÁRBOL JERÁRQUICO (Drill-down)
# ==========================================

# Definimos las 2 dimensiones disponibles. ALTO_VALOR ya no es una dimensión
# de árbol — es un filtro transversal (ver función principal más abajo).
DIMENSIONES_JERARQUICAS = {
    'GEOGRAFIA': [
        # (nombre_nivel, campo_id_orm, campo_nombre_orm)
        ('departamento', 'id_distrito_instalacion__id_provincia__id_departamento_id',
                          'id_distrito_instalacion__id_provincia__id_departamento__nombre'),
        ('provincia', 'id_distrito_instalacion__id_provincia_id',
                       'id_distrito_instalacion__id_provincia__nombre'),
        ('distrito', 'id_distrito_instalacion_id',
                      'id_distrito_instalacion__nombre'),
    ],
    'PRODUCTO': [
        ('campana', 'id_producto__nombre_campana', 'id_producto__nombre_campana'),
        ('tipo_solucion', 'id_producto__tipo_solucion', 'id_producto__tipo_solucion'),
        ('paquete', 'id_producto_id', 'id_producto__nombre_paquete'),
    ],
}


def obtener_nivel_jerarquico(
    *,
    estado_sot: str,
    dimension: str,
    nivel: int,
    anio: int = None,
    padre_id=None,
    solo_alto_valor: bool = False
) -> dict:
    """
    Resuelve el Gráfico 6: devuelve SOLO el nivel solicitado del árbol,
    nunca el árbol completo de golpe.

    - dimension: 'GEOGRAFIA' o 'PRODUCTO'
    - nivel: 0, 1, 2 (índice dentro de DIMENSIONES_JERARQUICAS[dimension])
    - padre_id: el ID/valor del nivel anterior seleccionado (None si es el nivel raíz)
    - solo_alto_valor: filtro transversal, no forma parte de la jerarquía
    """
    if dimension not in DIMENSIONES_JERARQUICAS:
        raise ValueError(f"Dimensión '{dimension}' no reconocida. Use 'GEOGRAFIA' o 'PRODUCTO'.")

    pasos = DIMENSIONES_JERARQUICAS[dimension]

    if nivel < 0 or nivel >= len(pasos):
        raise ValueError(f"Nivel {nivel} fuera de rango para la dimensión '{dimension}'.")

    nombre_nivel, campo_id, campo_nombre = pasos[nivel]

    queryset = Venta.objects.filter(
        id_estado_sot__codigo__iexact=estado_sot,
        activo=True
    )

    if anio:
        queryset = queryset.filter(fecha_real_inst__year=anio)

    if solo_alto_valor:
        # Filtro transversal: aplica sin importar la dimensión activa
        queryset = queryset.filter(id_producto__es_alto_valor=True)

    # Si hay un padre seleccionado, filtramos por el campo_id del nivel anterior
    if padre_id is not None and nivel > 0:
        _, campo_id_padre, _ = pasos[nivel - 1]
        queryset = queryset.filter(**{campo_id_padre: padre_id})

    resultado = list(
        queryset.values(
            item_id=F(campo_id),
            item_nombre=F(campo_nombre)
        ).annotate(
            total=Count('id')
        ).order_by('-total')
    )

    return {
        "dimension": dimension,
        "nivel": nombre_nivel,
        "indice_nivel": nivel,
        "tiene_siguiente_nivel": nivel < len(pasos) - 1,
        "items": resultado
    }
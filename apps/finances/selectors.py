from datetime import date
from django.db.models import QuerySet, Count, Sum, Q, F
from .models import Asistencia, ReglaComision, HistoricoPlanilla
from apps.sales.models import Venta # Ajusta según tu ruta
from apps.tracking.models import SeguimientoMensual # Ajusta según tu ruta

def obtener_asistencias_optimizadas() -> QuerySet:
    """
    Selector base para la grilla de asistencias.
    Trae los datos del usuario acoplados y excluye al nivel Gerencial (Dueño).
    """
    return Asistencia.objects.select_related(
        'id_usuario',
        'id_sucursal'
    ).filter(
        activo=True
    ).exclude(
        id_usuario__id_rol__codigo='DUENO'
    ).order_by('fecha', 'id_usuario__nombre_completo')


# ==========================================
# MOTOR DE LECTURA DE VENTAS (INSTALACIONES)
# ==========================================
def contar_ventas_instaladas_mes_actual(id_asesor: int, mes: int, anio: int) -> int:
    """
    Cuenta cuántas ventas logró instalar físicamente el asesor en el mes actual.
    Esta métrica es la que define si entra al 'Escenario Élite'.
    """
    return Venta.objects.filter(
        id_asesor_id=id_asesor,
        fecha_real_inst__month=mes,
        fecha_real_inst__year=anio,
        activo=True
    ).count()


# ==========================================
# MOTOR DE LECTURA DE COMISIONES (PAGOS)
# ==========================================
def obtener_ventas_pagadas_mes_anterior(id_asesor: int, mes: int, anio: int) -> QuerySet:
    """
    Trae las ventas PAGADAS del mes anterior.
    Aplica 3 JOINs vitales (Seguimiento -> Venta -> Producto) para obtener
    la comisión base y saber si es de alto valor sin hacer consultas N+1.
    """
    # 1. Calculamos cuál fue el mes y año anterior
    if mes == 1:
        mes_anterior = 12
        anio_anterior = anio - 1
    else:
        mes_anterior = mes - 1
        anio_anterior = anio

    # 2. Construimos la consulta partiendo desde SeguimientoMensual
    # porque es la única tabla que sabe si se pagó o no.
    return SeguimientoMensual.objects.select_related(
        'id_seguimiento__id_venta',
        'id_seguimiento__id_venta__id_producto'
    ).filter(
        # Tiene que ser la evaluación del Primer Mes del cliente
        mes_numero=1,
        # Tiene que estar pagado
        pago_cliente_realizado=True,
        # Filtramos por el asesor que hizo la venta
        id_seguimiento__id_venta__id_asesor_id=id_asesor,
        # La venta se tuvo que haber instalado el MES ANTERIOR
        id_seguimiento__id_venta__fecha_real_inst__month=mes_anterior,
        id_seguimiento__id_venta__fecha_real_inst__year=anio_anterior,
        # Reglas de integridad
        activo=True,
        id_seguimiento__activo=True,
        id_seguimiento__id_venta__activo=True
    )


def resumir_pozo_comisiones(ventas_pagadas_qs: QuerySet) -> dict:
    """
    Toma el QuerySet de ventas pagadas y lo exprime en memoria SQL
    para devolver el total de dinero base y cuántas son de Alto Valor.
    """
    resumen = ventas_pagadas_qs.aggregate(
        total_pagadas=Count('id'),
        dinero_bruto=Sum('id_seguimiento__id_venta__id_producto__comision_base'),
        # Contamos cuántas tienen la bandera de alto valor encendida
        total_alto_valor=Count(
            'id',
            filter=Q(id_seguimiento__id_venta__id_producto__es_alto_valor=True)
        )
    )

    return {
        "total_pagadas": resumen['total_pagadas'] or 0,
        "dinero_bruto": resumen['dinero_bruto'] or 0.00,
        "total_alto_valor": resumen['total_alto_valor'] or 0
    }


# ==========================================
# MOTOR DE LECTURA FINANCIERA (REGLAS Y PLANILLAS)
# ==========================================
def obtener_regla_comision_vigente(escenario: str, fecha_referencia: date) -> ReglaComision:
    """
    Busca la regla de comisión administrativa que estaba vigente en la fecha dada.
    Como el Admin puede crear reglas nuevas, siempre tomamos la más reciente
    cuyo periodo de inicio sea menor o igual al mes que estamos liquidando.
    """
    # Convertimos la fecha al día 1 del mes para asegurar comparación justa
    fecha_base = fecha_referencia.replace(day=1)

    return ReglaComision.objects.filter(
        escenario=escenario,
        periodo_inicio__lte=fecha_base,
        activo=True
    ).order_by('-periodo_inicio').first()


def obtener_planillas_mensuales_optimizadas() -> QuerySet:
    """
    Para la grilla de RRHH: Trae todas las planillas generadas con sus usuarios
    acoplados para evitar el N+1.
    """
    return HistoricoPlanilla.objects.select_related(
        'id_usuario',
        'procesado_por'
    ).all().order_by('-anio_fiscal', '-mes_fiscal', 'id_usuario__nombre_completo')
from decimal import Decimal
from typing import Optional
from datetime import date, timedelta
from django.db.models import QuerySet, Count, Sum, Q, F
from .models import Asistencia, ReglaComision, HistoricoPlanilla
from apps.sales.models import Venta
from apps.tracking.models import SeguimientoMensual

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
        fecha_real_inst__isnull=False,
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
    # 1. Cálculo robusto del mes anterior usando datetime
    fecha_evaluacion = date(anio, mes, 1)
    ultimo_dia_mes_anterior = fecha_evaluacion - timedelta(days=1)

    mes_anterior = ultimo_dia_mes_anterior.month
    anio_anterior = ultimo_dia_mes_anterior.year

    # 2. Construimos la consulta
    return SeguimientoMensual.objects.select_related(
        'id_seguimiento__id_venta',
        'id_seguimiento__id_venta__id_producto'
    ).filter(
        mes_numero=1,
        pago_cliente_realizado=True,
        id_seguimiento__id_venta__id_asesor_id=id_asesor,
        id_seguimiento__id_venta__fecha_real_inst__month=mes_anterior,
        id_seguimiento__id_venta__fecha_real_inst__year=anio_anterior,
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
        total_alto_valor=Count(
            'id',
            filter=Q(id_seguimiento__id_venta__id_producto__es_alto_valor=True)
        )
    )

    return {
        "total_pagadas": resumen['total_pagadas'] or 0,
        # <-- CRÍTICO: Fallback como Decimal para evitar TypeErrors en services.py
        "dinero_bruto": resumen['dinero_bruto'] or Decimal('0.00'),
        "total_alto_valor": resumen['total_alto_valor'] or 0
    }


# ==========================================
# MOTOR DE LECTURA FINANCIERA (REGLAS Y PLANILLAS)
# ==========================================
def obtener_regla_comision_vigente(escenario: str, fecha_referencia: date) -> Optional[ReglaComision]:
    """
    Busca la regla de comisión administrativa que estaba vigente en la fecha dada.
    Retorna None si RRHH olvidó configurarla.
    """
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
    # <-- Limpieza: .all() removido por ser redundante antes de order_by
    return HistoricoPlanilla.objects.select_related(
        'id_usuario',
        'procesado_por'
    ).order_by('-anio_fiscal', '-mes_fiscal', 'id_usuario__nombre_completo')


def contar_inasistencias_mes(id_asesor: int, mes: int, anio: int) -> int:
    """
    Cuenta los días que el asesor tiene estado asistio=False en el mes.
    """
    return Asistencia.objects.filter(
        id_usuario_id=id_asesor,
        fecha__month=mes,
        fecha__year=anio,
        asistio=False,
        activo=True
    ).count()
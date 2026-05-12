from datetime import date, timedelta
from dateutil.relativedelta import relativedelta


def calcular_dia_ciclo(dia_instalacion: int) -> int:
    """
    Regla 2A: Mapeo del día de instalación al día del ciclo de facturación.
    Diccionario actualizado con la nueva tabla operativa.
    """
    tabla_operativa = {
        1: 3, 2: 3,
        3: 4,
        4: 5,
        5: 8, 6: 8, 7: 8,
        8: 9,
        9: 11, 10: 11,
        11: 12,
        12: 14, 13: 14,
        14: 16, 15: 16,
        16: 18, 17: 18,
        18: 19,
        19: 20,
        20: 22, 21: 22,
        22: 24, 23: 24,
        24: 25,
        25: 26,
        26: 28, 27: 28,
        # Salto de mes implícito
        28: 1, 29: 1, 30: 1, 31: 1
    }

    return tabla_operativa.get(dia_instalacion, dia_instalacion)


def generar_fechas_proyectadas(fecha_real_instalacion: date) -> dict:
    """
    Regla 2: Genera la cabecera y los 6 registros mensuales basándose en el Día 0.
    """
    # ==========================================
    # 2A. CABECERA: Calcular el ciclo de facturación
    # ==========================================
    dia_ciclo = calcular_dia_ciclo(fecha_real_instalacion.day)

    # 🛡️ PROTECCIÓN DE SALTO DE MES
    if dia_ciclo < fecha_real_instalacion.day:
        # Si el día del ciclo (ej. 1) es menor al día de instalación (ej. 29)
        # Sumamos 1 mes entero y clavamos el día en 1.
        ciclo_facturacion = fecha_real_instalacion + relativedelta(months=1, day=dia_ciclo)
    else:
        # Si no, ocurre en el mismo mes (ej. Instalado el 4, Ciclo el 5).
        ciclo_facturacion = fecha_real_instalacion + relativedelta(day=dia_ciclo)

    meses = []

    # ==========================================
    # 2B. DETALLE: Mes 1 (Primer Registro)
    # ==========================================
    fecha_seg_m1 = ciclo_facturacion + timedelta(days=10)
    fecha_val_m1 = ciclo_facturacion + timedelta(days=18)

    meses.append({
        "mes_numero": 1,
        "fecha_seguimiento": fecha_seg_m1,
        "fecha_validacion_pago": fecha_val_m1
    })

    # ==========================================
    # 2C. DETALLE: Meses 2 al 6 (Regla EOM)
    # ==========================================
    # EL TRUCO ARQUITECTÓNICO: Para "recuperar el día original", no sumamos 1 mes
    # al registro anterior. Le sumamos (X meses) a la base original del Mes 1.
    base_fecha_val = fecha_val_m1

    for i in range(2, 7):  # Del mes 2 al 6

        # Fecha de Validación: Regla EOM (End of Month)
        # Ej: Enero 31 + relativedelta(months=1) = Feb 28
        # Ej: Enero 31 + relativedelta(months=2) = Mar 31 (¡Recupera el día 31!)
        nueva_fecha_val = base_fecha_val + relativedelta(months=(i - 1))

        # Fecha de Seguimiento: fecha_validacion_pago del registro ANTERIOR + 15 días
        nueva_fecha_seg = base_fecha_val + relativedelta(months=(i - 2)) + timedelta(days=15)

        meses.append({
            "mes_numero": i,
            "fecha_seguimiento": nueva_fecha_seg,
            "fecha_validacion_pago": nueva_fecha_val
        })

    # Retornamos el paquete completo listo para el Bulk Insert
    return {
        "ciclo_facturacion": ciclo_facturacion,
        "meses_detalle": meses
    }
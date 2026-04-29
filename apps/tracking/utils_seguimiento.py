from datetime import date, timedelta
from dateutil.relativedelta import relativedelta


def calcular_dia_ciclo(dia_instalacion: int) -> int:
    """
    Regla 2A: Mapeo del día de instalación al día del ciclo de facturación.
    """
    # Aquí puedes completar el diccionario con el resto de la tabla operativa de tu equipo
    tabla_operativa = {
        # Grupo de 3 días -> Salta al día 4
        1: 4, 2: 4, 3: 4,
        # Grupo de 2 días -> Salta al día 6
        4: 6, 5: 6,
        6: 9, 7: 9, 8: 9,
        9: 11, 10: 11,
        11: 14, 12: 14, 13: 14,
        14: 16, 15: 16,
        16: 19, 17: 19, 18: 19,
        19: 21, 20: 21,
        21: 24, 22: 24, 23: 24,
        24: 26, 25: 26,
        26: 29, 27: 29, 28: 29,
        29: 31, 30: 31, 31: 31
    }

    # Si por alguna razón envían un día que no está, devuelve el mismo día por defecto
    return tabla_operativa.get(dia_instalacion, dia_instalacion)


def generar_fechas_proyectadas(fecha_real_instalacion: date) -> dict:
    """
    Regla 2: Genera la cabecera y los 6 registros mensuales basándose en el Día 0.
    """
    # ==========================================
    # 2A. CABECERA: Calcular el ciclo de facturación
    # ==========================================
    dia_ciclo = calcular_dia_ciclo(fecha_real_instalacion.day)

    # Inyectamos el nuevo día. Usamos relativedelta por si el día resultante
    # es mayor a los días que tiene el mes (ej. día 31 en Febrero, lo ajusta al 28/29 automático)
    ciclo_facturacion = fecha_real_instalacion + relativedelta(day=dia_ciclo)

    meses = []

    # ==========================================
    # 2B. DETALLE: Mes 1 (Primer Registro)
    # ==========================================
    fecha_seg_m1 = ciclo_facturacion + timedelta(days=10)
    fecha_val_m1 = ciclo_facturacion + timedelta(days=20)

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
        fecha_val_anterior = meses[-1]["fecha_validacion_pago"]
        nueva_fecha_seg = fecha_val_anterior + timedelta(days=15)

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
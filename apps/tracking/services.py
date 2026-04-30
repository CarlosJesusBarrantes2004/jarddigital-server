from rest_framework.exceptions import ValidationError
from .models import SeguimientoMensual
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from .models import Seguimiento


def recalcular_fechas_por_nuevo_ciclo(seguimiento: Seguimiento, nuevo_ciclo):
    """
    Recalcula y actualiza los 6 meses existentes en la base de datos
    usando un nuevo ciclo de facturación como base.
    """
    # Obtenemos los meses ordenados del 1 al 6
    meses = list(seguimiento.meses_evaluados.order_by('mes_numero'))
    if not meses: return

    # --- Mes 1 (Depende directamente del ciclo) ---[cite: 1]
    m1 = meses[0]
    m1.fecha_seguimiento = nuevo_ciclo + timedelta(days=10)
    m1.fecha_validacion_pago = nuevo_ciclo + timedelta(days=20)
    m1.save()

    base_fecha_val = m1.fecha_validacion_pago

    # --- Meses 2 al 6 (Regla EOM Iterativa) ---[cite: 1]
    for i in range(1, len(meses)):  # Índices 1 al 5 (Meses 2 al 6)
        mes_actual = meses[i]
        mes_anterior = meses[i - 1]

        # Proyección exacta amarrada a la base del Mes 1
        nueva_fecha_val = base_fecha_val + relativedelta(months=mes_actual.mes_numero - 1)
        nueva_fecha_seg = mes_anterior.fecha_validacion_pago + timedelta(days=15)

        mes_actual.fecha_validacion_pago = nueva_fecha_val
        mes_actual.fecha_seguimiento = nueva_fecha_seg
        mes_actual.save()


def actualizar_seguimiento_mensual(*, mes_instance: SeguimientoMensual, datos_validados: dict,
                                   usuario_peticion) -> SeguimientoMensual:
    """
    Servicio encargado de actualizar un registro de Seguimiento Mensual
    aplicando las reglas estrictas de bloqueo de pagos.
    """
    nuevo_pago = datos_validados.get('pago_cliente_realizado', mes_instance.pago_cliente_realizado)

    # REGLA 3 y 4: Bloqueo/Desbloqueo de avance por pago
    # Si están intentando marcar o mantener este mes como pagado (True),
    # debemos verificar que el mes INMEDIATAMENTE ANTERIOR también esté pagado.
    if nuevo_pago is True and mes_instance.mes_numero > 1:

        # Buscamos el mes anterior en la base de datos
        mes_anterior = SeguimientoMensual.objects.filter(
            id_seguimiento=mes_instance.id_seguimiento,
            mes_numero=mes_instance.mes_numero - 1
        ).first()

        # Si el mes anterior existe y NO está pagado, levantamos el muro de contención
        if mes_anterior and not mes_anterior.pago_cliente_realizado:
            raise ValidationError({
                "pago_cliente_realizado": f"Regla de Secuencia: No puedes validar el pago del Mes {mes_instance.mes_numero} porque el Mes {mes_anterior.mes_numero} aún no registra pago."
            })

    # REGLA 5: La conformidad no requiere validación extra, ya que es independiente

    # Guardado Base
    for attr, value in datos_validados.items():
        setattr(mes_instance, attr, value)

    # (Opcional) Podemos estampar quién y cuándo modificó esto si tuvieran campos de auditoría

    mes_instance.save()
    return mes_instance
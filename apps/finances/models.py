from django.db import models
from django.conf import settings
from apps.core.models import Sucursal

class Asistencia(models.Model):
    id_usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, db_column="id_usuario")
    id_sucursal = models.ForeignKey(Sucursal, on_delete=models.PROTECT, db_column="id_sucursal")
    fecha = models.DateField()
    asistio = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)  # ¡Añadido para que RRHH pueda corregir errores!

    class Meta:
        db_table = "asistencia"


class ReglaRendimientoMensual(models.Model):
    nombre = models.CharField(max_length=150)
    anio = models.IntegerField()
    mes = models.IntegerField()

    # Gatillo
    min_instaladas = models.IntegerField()
    max_instaladas = models.IntegerField()

    # Consecuencias
    activa_sueldo_ft = models.BooleanField(default=False)
    monto_sueldo_ft = models.DecimalField(max_digits=10, decimal_places=2, default=1120.00)
    factor_comision_futura = models.DecimalField(max_digits=3, decimal_places=2)

    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "reglas_rendimiento_mensual"


class BolsaComisiones(models.Model):
    id_usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, db_column="id_usuario")
    mes_origen = models.IntegerField()
    anio_origen = models.IntegerField()

    total_ventas_pagadas = models.IntegerField()
    monto_bruto_generado = models.DecimalField(max_digits=10, decimal_places=2)

    id_regla_aplicada = models.ForeignKey(ReglaRendimientoMensual, on_delete=models.PROTECT,
                                          db_column="id_regla_aplicada")
    factor_aplicado = models.DecimalField(max_digits=3, decimal_places=2)
    monto_neto_guardado = models.DecimalField(max_digits=10, decimal_places=2)

    pagado = models.BooleanField(default=False)

    class Meta:
        db_table = "bolsa_comisiones"
        constraints = [
            # ¡El seguro anti-quiebra! Impide que a un usuario se le generen 2 bolsas el mismo mes/año.
            models.UniqueConstraint(fields=['id_usuario', 'mes_origen', 'anio_origen'], name='unica_bolsa_por_mes')
        ]


class LiquidacionMensualAsesor(models.Model):
    id_usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, db_column="id_usuario")
    mes = models.IntegerField()
    anio = models.IntegerField()

    # Sueldo Base
    total_instaladas_mes = models.IntegerField()
    sueldo_base_calculado = models.DecimalField(max_digits=10, decimal_places=2)

    # Comisiones (Relación 1 a 1 porque una bolsa se paga en una única liquidación)
    id_bolsa_pagada = models.OneToOneField(BolsaComisiones, on_delete=models.SET_NULL, null=True, blank=True,
                                           db_column="id_bolsa_pagada")
    monto_comisiones_pagado = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    # Totales
    monto_descuento_inasistencias = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    monto_final_pago = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_calculo = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "liquidacion_mensual_asesor"

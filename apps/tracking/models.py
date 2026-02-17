from django.db import models
from apps.sales.models import Venta

class Seguimiento(models.Model):
    # Relación 1 a 1: Una venta tiene un único registro maestro de seguimiento
    id_venta = models.OneToOneField(
        Venta,
        on_delete=models.CASCADE,
        related_name="seguimiento",
        db_column="id_venta"
    )
    codigo_pago = models.CharField(max_length=50, null=True, blank=True)
    ciclo_facturacion = models.CharField(max_length=20, null=True, blank=True)
    fecha_inicio = models.DateField(null=True, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "seguimiento"


class SeguimientoMensual(models.Model):
    id_seguimiento = models.ForeignKey(
        Seguimiento,
        on_delete=models.CASCADE,
        related_name="meses_evaluados",
        db_column="id_seguimiento"
    )
    mes_numero = models.IntegerField()
    pago_cliente_realizado = models.BooleanField(default=False)
    fecha_validacion_pago = models.DateField(null=True, blank=True)
    observacion = models.TextField(null=True, blank=True)
    activo = models.BooleanField(default=True) # ¡Salvavidas añadido!

    class Meta:
        db_table = "seguimiento_mensual"

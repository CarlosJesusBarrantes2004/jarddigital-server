from django.db import models
from django.conf import settings
from apps.core.models import Sucursal

# ==========================================
# 1. MÓDULO ASISTENCIAS
# ==========================================
class Asistencia(models.Model):
    id_usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, db_column="id_usuario")
    id_sucursal = models.ForeignKey(Sucursal, on_delete=models.PROTECT, db_column="id_sucursal")
    fecha = models.DateField()

    # True = Asistió | False = No Asistió | None = Vacío (Ignorado)
    asistio = models.BooleanField(null=True, blank=True, default=None)
    activo = models.BooleanField(default=True)

    # Sellos de auditoría silenciosos
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "asistencia"
        unique_together = ('id_usuario', 'fecha')


# ==========================================
# 2. MOTOR DE CONFIGURACIÓN FINANCIERA
# ==========================================
class ReglaComision(models.Model):
    """
    Reemplaza a ReglaRendimientoMensual.
    Almacena los umbrales dinámicos que el Administrador puede cambiar mes a mes.
    """
    ESCENARIO_CHOICES = [
        ('ESTANDAR', 'Escenario Estándar (< 20 Inst.)'),
        ('ELITE', 'Escenario Élite (>= 20 Inst.)'),
    ]

    periodo_inicio = models.DateField(help_text="Mes/Año desde que rige esta regla (Día 1)")
    escenario = models.CharField(max_length=15, choices=ESCENARIO_CHOICES)

    # Umbrales de Ventas Pagadas (Para definir % del pozo)
    min_ventas_pagadas_medio = models.PositiveIntegerField(help_text="Mínimo para cobrar el 50%")
    min_ventas_pagadas_optimo = models.PositiveIntegerField(help_text="Mínimo para cobrar el 100%")

    # Umbrales de Alto Valor (Para definir multiplicador final)
    alto_valor_nivel_1 = models.PositiveIntegerField(
        help_text="Cantidad mínima para NO ser castigado al 90% (o mantener 90% en élite)")
    alto_valor_nivel_2 = models.PositiveIntegerField(help_text="Cantidad para subir a 100%")
    alto_valor_nivel_3 = models.PositiveIntegerField(help_text="Cantidad para subir a 110%")

    # Valores Financieros
    sueldo_base_elite = models.DecimalField(max_digits=10, decimal_places=2, default=1130.00)

    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "fin_regla_comision"
        ordering = ['-periodo_inicio']

    def __str__(self):
        return f"Regla {self.escenario} - Desde {self.periodo_inicio.strftime('%m/%Y')}"


# ==========================================
# 3. CONSOLIDACIÓN DE PAGOS
# ==========================================
class HistoricoPlanilla(models.Model):
    """
    Reemplaza a BolsaComisiones y LiquidacionMensualAsesor.
    Fotografía inmutable del pago de un asesor en un mes específico.
    """
    id_usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, db_column="id_usuario")
    mes_fiscal = models.PositiveSmallIntegerField(help_text="Mes en el que se DEPOSITA el dinero")
    anio_fiscal = models.PositiveIntegerField()

    # --- 1. Métricas que justifican la decisión matemática ---
    ventas_instaladas_mes_actual = models.PositiveSmallIntegerField(help_text="Define si aplica Élite o Estándar")
    ventas_pagadas_mes_anterior = models.PositiveSmallIntegerField(help_text="Define el % del pozo")
    ventas_alto_valor_pagadas = models.PositiveSmallIntegerField(default=0, help_text="Define multiplicador 90/100/110")
    cantidad_faltas = models.PositiveSmallIntegerField(help_text="Días de inasistencia (asistio=False)")

    # --- 2. Factores de Cálculo Aplicados (Auditoría) ---
    sueldo_base_aplicado = models.DecimalField(max_digits=10, decimal_places=2)
    porcentaje_pozo_aplicado = models.DecimalField(max_digits=5, decimal_places=2, help_text="0.00, 50.00 o 100.00")
    multiplicador_alto_valor = models.DecimalField(max_digits=5, decimal_places=2, help_text="90.00, 100.00 o 110.00")

    # --- 3. Resultados Financieros ---
    pozo_comisiones_bruto = models.DecimalField(max_digits=10, decimal_places=2,
                                                help_text="Suma pura de productos antes de multiplicadores")
    comision_neta_ganada = models.DecimalField(max_digits=10, decimal_places=2,
                                               help_text="Pozo * % Pozo * Multiplicador")
    descuento_inasistencias = models.DecimalField(max_digits=10, decimal_places=2)

    # SUELDO FINAL A DEPOSITAR
    sueldo_neto_final = models.DecimalField(max_digits=10, decimal_places=2)

    # --- 4. Sellos ---
    fecha_liquidacion = models.DateTimeField(auto_now_add=True)
    procesado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                      related_name="planillas_procesadas", db_column="procesado_por")

    class Meta:
        db_table = "fin_historico_planilla"
        constraints = [
            # Tu seguro anti-quiebra adaptado a la nueva tabla
            models.UniqueConstraint(fields=['id_usuario', 'mes_fiscal', 'anio_fiscal'], name='unica_planilla_por_mes')
        ]

    def __str__(self):
        return f"Planilla {self.id_usuario} - {self.mes_fiscal}/{self.anio_fiscal} - S/ {self.sueldo_neto_final}"

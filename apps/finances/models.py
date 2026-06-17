from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.core.models import Sucursal, Modalidad  # Ajusta el import


# ==========================================
# 1. MÓDULO ASISTENCIAS
# ==========================================
class Asistencia(models.Model):
    id_usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, db_column="id_usuario")
    # Mantenemos id_sucursal aquí para conservar la "fotografía histórica" de dónde marcó asistencia.
    id_sucursal = models.ForeignKey(Sucursal, on_delete=models.PROTECT, db_column="id_sucursal")
    fecha = models.DateField()

    # True = Asistió | False = No Asistió | None = Vacío (Ignorado)
    asistio = models.BooleanField(null=True, blank=True, default=None)
    activo = models.BooleanField(default=True)

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "asistencia"
        unique_together = ('id_usuario', 'fecha')


# ==========================================
# 2. MOTOR DE CONFIGURACIÓN FINANCIERA
# ==========================================
class ReglaComision(models.Model):
    ESCENARIO_CHOICES = [
        ('ESTANDAR', 'Escenario Estándar (< 20 Inst.)'),
        ('ELITE', 'Escenario Élite (>= 20 Inst.)'),
    ]

    periodo_inicio = models.DateField(help_text="Mes/Año desde que rige esta regla (Día 1)")
    escenario = models.CharField(max_length=15, choices=ESCENARIO_CHOICES)

    # ---> LA NUEVA PIEZA ARQUITECTÓNICA <---
    id_modalidad = models.ForeignKey(
        Modalidad,
        on_delete=models.PROTECT,
        db_column='id_modalidad',
        help_text="Modalidad a la que aplica esta regla (Ej: CALL o CAMPO)"
    )

    min_ventas_pagadas_medio = models.PositiveIntegerField(help_text="Mínimo para cobrar el 50%")
    min_ventas_pagadas_optimo = models.PositiveIntegerField(help_text="Mínimo para cobrar el 100%")

    alto_valor_nivel_1 = models.PositiveIntegerField(
        help_text="Cantidad mínima para NO ser castigado al 90% (o mantener 90% en élite)")
    alto_valor_nivel_2 = models.PositiveIntegerField(help_text="Cantidad para subir a 100%")
    alto_valor_nivel_3 = models.PositiveIntegerField(help_text="Cantidad para subir a 110%")

    sueldo_base_elite = models.DecimalField(max_digits=10, decimal_places=2, default=1130.00)

    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "fin_regla_comision"
        ordering = ['-periodo_inicio']
        constraints = [
            # FIX: La nueva tríada perfecta anti-duplicados.
            # Permite tener: "2026-06-01 + ESTANDAR + CALL" y "2026-06-01 + ESTANDAR + CAMPO"
            models.UniqueConstraint(
                fields=['periodo_inicio', 'escenario', 'id_modalidad'],
                name='unica_regla_por_periodo_escenario_modalidad'
            )
        ]

    def __str__(self):
        # Ahora el string de la consola mostrará claramente a quién pertenece
        return f"Regla {self.escenario} ({self.id_modalidad.codigo}) - Desde {self.periodo_inicio.strftime('%m/%Y')}"


# ==========================================
# 3. CONSOLIDACIÓN DE PAGOS
# ==========================================
class HistoricoPlanilla(models.Model):
    id_usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, db_column="id_usuario")

    # FIX 3: Validadores de rango para el mes
    mes_fiscal = models.PositiveSmallIntegerField(
        help_text="Mes en el que se DEPOSITA el dinero",
        validators=[MinValueValidator(1), MaxValueValidator(12)]
    )
    anio_fiscal = models.PositiveIntegerField()

    ventas_instaladas_mes_actual = models.PositiveSmallIntegerField(help_text="Define si aplica Élite o Estándar")
    ventas_pagadas_mes_anterior = models.PositiveSmallIntegerField(help_text="Define el % del pozo")
    ventas_alto_valor_pagadas = models.PositiveSmallIntegerField(default=0, help_text="Define multiplicador 90/100/110")
    cantidad_faltas = models.PositiveSmallIntegerField(help_text="Días de inasistencia (asistio=False)")

    sueldo_base_aplicado = models.DecimalField(max_digits=10, decimal_places=2)

    # FIX 4: Claridad absoluta en el almacenamiento de factores
    porcentaje_pozo_aplicado = models.DecimalField(max_digits=4, decimal_places=2,
                                                   help_text="Factor matemático: 0.00, 0.50 o 1.00")
    multiplicador_alto_valor = models.DecimalField(max_digits=4, decimal_places=2,
                                                   help_text="Factor matemático: 0.90, 1.00 o 1.10")

    pozo_comisiones_bruto = models.DecimalField(max_digits=10, decimal_places=2,
                                                help_text="Suma pura de productos antes de multiplicadores")
    comision_neta_ganada = models.DecimalField(max_digits=10, decimal_places=2,
                                               help_text="Pozo * % Pozo * Multiplicador")
    descuento_inasistencias = models.DecimalField(max_digits=10, decimal_places=2)

    sueldo_neto_final = models.DecimalField(max_digits=10, decimal_places=2)

    fecha_liquidacion = models.DateTimeField(auto_now_add=True)

    # FIX 5: Retirado el db_column="procesado_por" para que Django asigne procesado_por_id
    procesado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                      related_name="planillas_procesadas")

    class Meta:
        db_table = "fin_historico_planilla"
        constraints = [
            models.UniqueConstraint(fields=['id_usuario', 'mes_fiscal', 'anio_fiscal'], name='unica_planilla_por_mes')
        ]

    def __str__(self):
        return f"Planilla {self.id_usuario} - {self.mes_fiscal}/{self.anio_fiscal} - S/ {self.sueldo_neto_final}"
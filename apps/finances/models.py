from django.db import models
from django.conf import settings
from apps.core.models import Sucursal

class ReglaSalarialMensual(models.Model):
    anio = models.IntegerField()
    mes = models.IntegerField()
    dias_laborables_mes = models.IntegerField(default=30)

    class Meta:
        db_table = 'reglas_salariales_mensual'

class EscalaSueldo(models.Model):
    id_regla_salarial = models.ForeignKey(ReglaSalarialMensual, on_delete=models.CASCADE)
    nombre_escala = models.CharField(max_length=50) # Bronce, Plata...
    minimo_ventas_requeridas = models.IntegerField()
    sueldo_base_nivel = models.DecimalField(max_digits=10, decimal_places=2)
    porcentaje_comision = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        db_table = 'escalas_sueldo'

class Asistencia(models.Model):
    id_usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="asistencias"
    )
    id_sucursal = models.ForeignKey(
        Sucursal, on_delete=models.CASCADE, related_name="asistencias"
    )
    fecha = models.DateField()
    asistio = models.BooleanField(default=False)

    class Meta:
        db_table = "asistencia"

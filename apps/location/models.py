from django.db import models
from django.conf import settings


class Sucursal(models.Model):
    nombre = models.CharField(max_length=100)
    direccion = models.CharField(max_length=255)

    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "sucursales"


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


class Modalidad(models.Model):
    nombre = models.CharField(max_length=50)  # CALL, CAMPO
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "modalidades"


class ModalidadSede(models.Model):
    id_sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE)
    id_modalidad = models.ForeignKey(Modalidad, on_delete=models.CASCADE)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "modalidades_sede"


class SupervisorAsignacion(models.Model):
    id_modalidad_sede = models.ForeignKey(ModalidadSede, on_delete=models.CASCADE)
    id_supervisor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE
    )
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "supervisor_asignacion"

from django.db import models
from django.conf import settings

class Sucursal(models.Model):
    nombre = models.CharField(max_length=100)
    direccion = models.CharField(max_length=255)

    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "sucursales"


class Modalidad(models.Model):
    nombre = models.CharField(max_length=50) # Ej: CALL CENTER, CAMPO
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "modalidades"

class ModalidadSede(models.Model):
    id_sucursal = models.ForeignKey('Sucursal', on_delete=models.CASCADE)
    id_modalidad = models.ForeignKey(Modalidad, on_delete=models.CASCADE)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "modalidades_sede"


class TipoDocumento(models.Model):
    codigo = models.CharField(max_length=10, unique=True) # Ej: DNI, RUC, CE
    nombre = models.CharField(max_length=50)
    longitud_exacta = models.IntegerField(null=True, blank=True) # 8 para DNI, 11 para RUC
    regex_validacion = models.CharField(max_length=100, null=True, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "tipos_documento"
        ordering = ['id']

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"
from django.db import models

class Departamento(models.Model):
    codigo_ubigeo = models.CharField(max_length=2, unique=True)
    nombre = models.CharField(max_length=100)

    class Meta:
        db_table = "departamentos"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Provincia(models.Model):
    id_departamento = models.ForeignKey(
        Departamento, on_delete=models.CASCADE, related_name="provincias"
    )
    codigo_ubigeo = models.CharField(max_length=4, unique=True)
    nombre = models.CharField(max_length=100)

    class Meta:
        db_table = "provincias"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Distrito(models.Model):
    id_provincia = models.ForeignKey(
        Provincia, on_delete=models.CASCADE, related_name="distritos"
    )
    codigo_ubigeo = models.CharField(max_length=6, unique=True, help_text="UBIGEO completo INEI")
    nombre = models.CharField(max_length=100)

    class Meta:
        db_table = "distritos"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre
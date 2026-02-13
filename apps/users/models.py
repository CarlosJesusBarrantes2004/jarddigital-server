from django.db import models
from django.contrib.auth.models import AbstractUser


class RolSistema(models.Model):
    codigo = models.CharField(max_length=20, unique=True)  # DUEÑO, ASESOR, etc.
    nombre = models.CharField(max_length=100)
    nivel_jerarquia = models.IntegerField()
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "roles_sistema"


class Usuario(AbstractUser):
    nombre_completo = models.CharField(max_length=255)
    id_rol = models.ForeignKey(
        RolSistema, on_delete=models.PROTECT, null=True, related_name="usuarios"
    )
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "usuarios"

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from apps.location.models import ModalidadSede

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

class PermisoAcceso(models.Model):
    # Aquí unimos al usuario con la sede a través del related_name="permisos"
    id_usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="permisos"
    )
    id_modalidad_sede = models.ForeignKey(ModalidadSede, on_delete=models.CASCADE)

    class Meta:
        db_table = "permisos_acceso"
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from apps.core.models import ModalidadSede


class RolSistema(models.Model):
    codigo = models.CharField(max_length=20, unique=True)  # DUEÑO, ASESOR, etc.
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True) # ¡Añadido del nuevo DBML!
    nivel_jerarquia = models.IntegerField()
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "roles_sistema"


class Usuario(AbstractUser):
    nombre_completo = models.CharField(max_length=255)
    id_rol = models.ForeignKey(
        RolSistema,
        on_delete=models.PROTECT,
        null=True,
        related_name="usuarios",
        db_column="id_rol" # ¡Evita que se llame id_rol_id!
    )
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "usuarios"


class PerfilLaboral(models.Model):
    id_usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='perfil_laboral',
        db_column="id_usuario"
    )
    sueldo_base_part_time = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_inicio_contrato = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'perfiles_laborales'


class PermisoAcceso(models.Model):
    id_usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="permisos",
        db_column="id_usuario"
    )
    id_modalidad_sede = models.ForeignKey(
        ModalidadSede,
        on_delete=models.CASCADE,
        db_column="id_modalidad_sede"
    )

    class Meta:
        db_table = "permisos_acceso"


class SupervisorAsignacion(models.Model):
    id_modalidad_sede = models.ForeignKey(
        ModalidadSede,
        on_delete=models.CASCADE,
        db_column="id_modalidad_sede"
    )
    id_supervisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="asignaciones_supervisor",
        db_column="id_supervisor"
    )
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "supervisor_asignacion"

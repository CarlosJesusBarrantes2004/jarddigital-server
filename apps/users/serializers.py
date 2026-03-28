from django.db import transaction
from django.contrib.auth.hashers import make_password
from rest_framework import serializers
from .models import Usuario, RolSistema, PermisoAcceso, SupervisorAsignacion
from .services import crear_usuario_admin, actualizar_usuario_admin
from apps.core.models import Sucursal, ModalidadSede
from drf_spectacular.utils import extend_schema_field

class RolSistemaSerializer(serializers.ModelSerializer):
    class Meta:
        model = RolSistema
        fields = ["id", "codigo", "nombre", "descripcion", "nivel_jerarquia", "activo"]


# 1. Creamos la estructura visual para Swagger y el Frontend
class SucursalModalidadSerializer(serializers.Serializer):
    id_modalidad_sede = serializers.IntegerField()
    id_sucursal = serializers.IntegerField()
    nombre_sucursal = serializers.CharField()
    id_modalidad = serializers.IntegerField()
    nombre_modalidad = serializers.CharField()


class SucursalesMixin:
    """Mixin para no repetir el código de obtener sucursales en RAM"""
    @extend_schema_field('SucursalModalidadSerializer(many=True)')
    def get_sucursales(self, obj):
        permisos = obj.permisos.all()
        resultado = []
        for permiso in permisos:
            mod_sede = permiso.id_modalidad_sede
            if mod_sede.activo and mod_sede.id_sucursal.activo and mod_sede.id_modalidad.activo:
                resultado.append({
                    "id_modalidad_sede": mod_sede.id,
                    "id_sucursal": mod_sede.id_sucursal.id,
                    "nombre_sucursal": mod_sede.id_sucursal.nombre,
                    "id_modalidad": mod_sede.id_modalidad.id,
                    "nombre_modalidad": mod_sede.id_modalidad.nombre
                })
        return resultado


class UsuarioSerializer(SucursalesMixin, serializers.ModelSerializer):
    rol = RolSistemaSerializer(source="id_rol", read_only=True)
    sucursales = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = ["id", "username", "nombre_completo", "email", "rol", 'fecha_nacimiento', 'celular', "activo", "sucursales"]


class UsuarioAdminSerializer(SucursalesMixin, serializers.ModelSerializer):
    ids_modalidades_sede = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)
    password = serializers.CharField(write_only=True, required=False)
    sucursales = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = ['id', 'username', 'password', "celular", 'nombre_completo', 'email', 'id_rol', 'activo', 'ids_modalidades_sede', 'sucursales']

    # ¡Mira lo limpio que queda esto! El serializador delega el trabajo pesado al servicio.
    def create(self, validated_data):
        return crear_usuario_admin(datos_validados=validated_data)

    def update(self, instance, validated_data):
        return actualizar_usuario_admin(usuario=instance, datos_validados=validated_data)

class SupervisorAsignacionSerializer(serializers.ModelSerializer):
    # Campos de solo lectura para que la tabla del frontend se pinte sola
    nombre_supervisor = serializers.CharField(source='id_supervisor.nombre_completo', read_only=True)
    nombre_sucursal = serializers.CharField(source='id_modalidad_sede.id_sucursal.nombre', read_only=True)
    nombre_modalidad = serializers.CharField(source='id_modalidad_sede.id_modalidad.nombre', read_only=True)

    class Meta:
        model = SupervisorAsignacion
        fields = [
            'id',
            'id_modalidad_sede', 'nombre_sucursal', 'nombre_modalidad',
            'id_supervisor', 'nombre_supervisor',
            'fecha_inicio', 'fecha_fin', 'activo'
        ]

    def validate(self, data):
        # Validación de negocio: La fecha de inicio no puede ser mayor a la de fin
        if data.get('fecha_fin') and data.get('fecha_inicio') > data.get('fecha_fin'):
            raise serializers.ValidationError({"fecha_fin": "La fecha de fin no puede ser anterior a la fecha de inicio."})
        return data
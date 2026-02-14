from rest_framework import serializers
from .models import Usuario, RolSistema
from apps.core.models import Sucursal, ModalidadSede
from drf_spectacular.utils import extend_schema_field

class RolSistemaSerializer(serializers.ModelSerializer):
    class Meta:
        model = RolSistema
        fields = ["id", "codigo", "nombre", "nivel_jerarquia"]


# 1. Creamos la estructura visual para Swagger y el Frontend
class SucursalModalidadSerializer(serializers.Serializer):
    id_sucursal = serializers.IntegerField()
    nombre_sucursal = serializers.CharField()
    id_modalidad = serializers.IntegerField()
    nombre_modalidad = serializers.CharField()


class UsuarioSerializer(serializers.ModelSerializer):
    rol = RolSistemaSerializer(source="id_rol", read_only=True)
    sucursales = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = [
            "id",
            "username",
            "nombre_completo",
            "email",
            "rol",
            "activo",
            "sucursales",
        ]

    # 2. Le decimos a Swagger que use la nueva estructura
    @extend_schema_field(SucursalModalidadSerializer(many=True))
    def get_sucursales(self, obj):
        # 3. Viajamos por los permisos trayendo Sucursal y Modalidad en UNA sola consulta (JOIN)
        # Filtramos para asegurarnos de que todo en la cadena siga activo
        permisos_activos = obj.permisos.filter(
            id_modalidad_sede__activo=True,
            id_modalidad_sede__id_sucursal__activo=True,
            id_modalidad_sede__id_modalidad__activo=True
        ).select_related(
            'id_modalidad_sede__id_sucursal',
            'id_modalidad_sede__id_modalidad'
        )

        # 4. Armamos el array con la data combinada para tu compañero
        resultado = []
        for permiso in permisos_activos:
            mod_sede = permiso.id_modalidad_sede
            resultado.append({
                "id_sucursal": mod_sede.id_sucursal.id,
                "nombre_sucursal": mod_sede.id_sucursal.nombre,
                "id_modalidad": mod_sede.id_modalidad.id,
                "nombre_modalidad": mod_sede.id_modalidad.nombre
            })

        return resultado


class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = Usuario
        fields = [
            "username",
            "password",
            "nombre_completo",
            "email",
            "id_rol",
            "activo",
        ]

    def create(self, validated_data):
        password = validated_data.pop("password")

        user = Usuario.objects.create_user(password=password, **validated_data)
        return user

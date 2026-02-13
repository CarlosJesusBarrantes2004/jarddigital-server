from rest_framework import serializers
from .models import Usuario, RolSistema
from apps.core.models import Sucursal, ModalidadSede
from drf_spectacular.utils import extend_schema_field

class RolSistemaSerializer(serializers.ModelSerializer):
    class Meta:
        model = RolSistema
        fields = ["id", "codigo", "nombre", "nivel_jerarquia"]


class SucursalSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sucursal
        fields = ["id", "nombre"]


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

    @extend_schema_field(SucursalSimpleSerializer(many=True))
    def get_sucursales(self, obj):
        # 1. Buscamos a qué "Modalidades-Sede" tiene permiso este usuario
        modalidades_sede_ids = obj.permisos.values_list("id_modalidad_sede", flat=True)

        # Si es un usuario nuevo y no tiene permisos, devolvemos lista vacía
        if not modalidades_sede_ids:
            return []

        # 2. Extraemos solo los IDs de las sucursales únicas de esas modalidades
        sucursales_ids = ModalidadSede.objects.filter(
            id__in=modalidades_sede_ids,
            activo=True
        ).values_list("id_sucursal", flat=True).distinct()

        # 3. Traemos la info de esas sucursales
        queryset = Sucursal.objects.filter(id__in=sucursales_ids, activo=True)
        return SucursalSimpleSerializer(queryset, many=True).data


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

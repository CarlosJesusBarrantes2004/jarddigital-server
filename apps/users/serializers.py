from rest_framework import serializers
from .models import Usuario, RolSistema
from location.models import Sucursal


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

    def get_sucursales(self, obj):
        sucursales_ids = obj.asistencias.values_list(
            "id_sucursal", flat=True
        ).distinct()
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

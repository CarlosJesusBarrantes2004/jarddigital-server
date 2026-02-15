from django.db import transaction
from django.contrib.auth.hashers import make_password
from rest_framework import serializers
from .models import Usuario, RolSistema, PermisoAcceso
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


class UsuarioAdminSerializer(serializers.ModelSerializer):
    ids_modalidades_sede = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )
    password = serializers.CharField(write_only=True, required=False)

    # 1. Agregamos el campo de solo lectura para el GET
    sucursales = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = [
            'id', 'username', 'password', 'nombre_completo', 'email',
            'id_rol', 'activo', 'ids_modalidades_sede', 'sucursales'  # <- Añadido aquí
        ]

    # 2. Reutilizamos la lógica que ya teníamos (Asegúrate de tener importado SucursalModalidadSerializer)
    @extend_schema_field(SucursalModalidadSerializer(many=True))
    def get_sucursales(self, obj):
        permisos_activos = obj.permisos.filter(
            id_modalidad_sede__activo=True,
            id_modalidad_sede__id_sucursal__activo=True,
            id_modalidad_sede__id_modalidad__activo=True
        )

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

    def create(self, validated_data):
        ids_sedes = validated_data.pop('ids_modalidades_sede', [])
        password = validated_data.pop('password', None)

        with transaction.atomic():
            usuario = Usuario(**validated_data)
            if password:
                usuario.set_password(password)
            usuario.save()

            permisos = [PermisoAcceso(id_usuario=usuario, id_modalidad_sede_id=mod_id) for mod_id in ids_sedes]
            if permisos:
                PermisoAcceso.objects.bulk_create(permisos)

        return usuario

    def update(self, instance, validated_data):
        # 1. Extraemos los campos especiales
        ids_sedes = validated_data.pop('ids_modalidades_sede', None)
        password = validated_data.pop('password', None)

        with transaction.atomic():
            # 2. Actualizamos datos básicos (nombre, email, rol, etc.)
            for attr, value in validated_data.items():
                setattr(instance, attr, value)

            # 3. Si mandaron contraseña nueva, la encriptamos
            if password:
                instance.set_password(password)

            instance.save()

            # 4. LA MAGIA: Si mandaron un nuevo array de sedes, hacemos Clear & Replace
            if ids_sedes is not None:
                # Borramos los permisos viejos
                PermisoAcceso.objects.filter(id_usuario=instance).delete()
                # Creamos los nuevos
                permisos = [PermisoAcceso(id_usuario=instance, id_modalidad_sede_id=mod_id) for mod_id in ids_sedes]
                if permisos:
                    PermisoAcceso.objects.bulk_create(permisos)

        return instance
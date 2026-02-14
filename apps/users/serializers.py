from rest_framework import serializers
from django.db import transaction
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


class UserRegisterSerializer(serializers.ModelSerializer):
    # 1. Agregamos el campo para recibir los IDs (solo de escritura, no se devuelve en el GET)
    ids_modalidades_sede = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False  # Opcional, por si creas al Dueño y no necesita sede
    )

    class Meta:
        model = Usuario
        fields = [
            'username', 'password', 'nombre_completo', 'email',
            'id_rol', 'activo', 'ids_modalidades_sede'
        ]

    def create(self, validated_data):
        # 2. Separamos los IDs de la data del usuario antes de guardarlo
        ids_sedes = validated_data.pop('ids_modalidades_sede', [])
        password = validated_data.pop('password', None)

        # 3. ¡EL ESCUDO PROTECTOR! (Transacción atómica)
        with transaction.atomic():
            # Paso A: Creamos el usuario
            usuario = Usuario(**validated_data)
            if password:
                usuario.set_password(password)  # Encriptamos la clave
            usuario.save()

            # Paso B: Creamos los permisos de acceso a las sedes
            permisos_a_crear = []
            for mod_id in ids_sedes:
                permisos_a_crear.append(
                    PermisoAcceso(id_usuario=usuario, id_modalidad_sede_id=mod_id)
                )

            # bulk_create hace un solo INSERT masivo en SQL (Super optimizado)
            if permisos_a_crear:
                PermisoAcceso.objects.bulk_create(permisos_a_crear)

        return usuario
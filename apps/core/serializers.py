from django.db import transaction
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import Sucursal, Modalidad, TipoDocumento, ModalidadSede

# 1. El esquema visual para Swagger
class ModalidadMiniSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nombre = serializers.CharField()


class SucursalSerializer(serializers.ModelSerializer):
    # 2. El array que recibe el backend para crear/editar (Write Only)
    ids_modalidades = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    # 3. Lo que devolvemos al frontend para que pinte la tabla (Read Only)
    modalidades = serializers.SerializerMethodField()

    class Meta:
        model = Sucursal
        fields = ['id', 'nombre', 'direccion', 'activo', 'creado_en', 'ids_modalidades', 'modalidades']

    @extend_schema_field(ModalidadMiniSerializer(many=True))
    def get_modalidades(self, obj):

        relaciones = obj.modalidades_sede.all()

        return [
            {"id": rel.id_modalidad.id, "nombre": rel.id_modalidad.nombre}
            for rel in relaciones
            if rel.activo and rel.id_modalidad.activo  # Filtramos en memoria, no en BD
        ]

    def create(self, validated_data):
        ids_mods = validated_data.pop('ids_modalidades', [])

        with transaction.atomic():
            sucursal = Sucursal.objects.create(**validated_data)

            # Creamos las relaciones puente en ModalidadSede
            relaciones = [
                ModalidadSede(id_sucursal=sucursal, id_modalidad_id=mod_id)
                for mod_id in ids_mods
            ]
            if relaciones:
                ModalidadSede.objects.bulk_create(relaciones)

        return sucursal

    def update(self, instance, validated_data):
        ids_mods = validated_data.pop('ids_modalidades', None)

        with transaction.atomic():
            # 1. Actualizamos los campos normales de la sucursal (ej. el nombre)
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

            # 2. LA MAGIA EVOLUCIONADA: Sincronización Inteligente (Sin borrar)
            if ids_mods is not None:
                # Obtenemos lo que ya existe en la base de datos
                relaciones_actuales = ModalidadSede.objects.filter(id_sucursal=instance)
                ids_actuales = set(relaciones_actuales.values_list('id_modalidad_id', flat=True))
                ids_nuevos = set(ids_mods)

                # A) DESACTIVAR: Modalidades que antes estaban, pero ya no vienen en el JSON
                ids_a_desactivar = ids_actuales - ids_nuevos
                if ids_a_desactivar:
                    relaciones_actuales.filter(id_modalidad_id__in=ids_a_desactivar).update(activo=False)

                # B) REACTIVAR: Modalidades que ya existían y vuelven a venir en el JSON
                ids_a_mantener = ids_actuales & ids_nuevos
                if ids_a_mantener:
                    relaciones_actuales.filter(id_modalidad_id__in=ids_a_mantener).update(activo=True)

                # C) CREAR: Modalidades totalmente nuevas
                ids_a_crear = ids_nuevos - ids_actuales
                if ids_a_crear:
                    relaciones_nuevas = [
                        ModalidadSede(id_sucursal=instance, id_modalidad_id=mod_id)
                        for mod_id in ids_a_crear
                    ]
                    ModalidadSede.objects.bulk_create(relaciones_nuevas)

        return instance


class ModalidadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Modalidad
        fields = '__all__'

class TipoDocumentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoDocumento
        fields = ['id', 'codigo', 'nombre', 'longitud_exacta', 'regex_validacion', 'activo']

class ModalidadSedeOpcionesSerializer(serializers.ModelSerializer):
    # Creamos un campo virtual bonito para el frontend
    etiqueta = serializers.SerializerMethodField()

    class Meta:
        model = ModalidadSede
        fields = ['id', 'etiqueta']

    def get_etiqueta(self, obj) -> str:
        # Esto devolverá algo como: "Sede Principal Chiclayo - CALL CENTER"
        return f"{obj.id_sucursal.nombre} - {obj.id_modalidad.nombre}"
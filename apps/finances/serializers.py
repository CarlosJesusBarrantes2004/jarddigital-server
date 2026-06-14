from rest_framework import serializers
from apps.users.models import Usuario
from .models import Asistencia, ReglaComision, HistoricoPlanilla

class AsistenciaLecturaSerializer(serializers.ModelSerializer):
    nombre_asesor = serializers.CharField(source='id_usuario.nombre_completo', read_only=True)

    class Meta:
        model = Asistencia
        fields = ['id', 'id_usuario', 'nombre_asesor', 'fecha', 'asistio']

class AsistenciaUpsertSerializer(serializers.Serializer):
    # Validamos que el ID exista realmente en la BD
    id_usuario = serializers.PrimaryKeyRelatedField(queryset=Usuario.objects.all())
    fecha = serializers.DateField()
    asistio = serializers.BooleanField(allow_null=True, required=False, default=None)


class ReglaComisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReglaComision
        fields = '__all__'

class HistoricoPlanillaSerializer(serializers.ModelSerializer):
    # Agregamos los nombres para que el frontend no tenga que cruzar IDs
    nombre_asesor = serializers.CharField(source='id_usuario.nombre_completo', read_only=True)
    nombre_rrhh = serializers.CharField(source='procesado_por.nombre_completo', read_only=True)

    class Meta:
        model = HistoricoPlanilla
        fields = '__all__'
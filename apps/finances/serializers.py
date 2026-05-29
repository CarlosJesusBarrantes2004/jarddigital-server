from rest_framework import serializers
from apps.users.models import Usuario # Ajusta el import a tu ruta
from .models import Asistencia

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
from rest_framework import serializers
from .models import Sucursal, Modalidad

class SucursalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sucursal
        fields = '__all__'  # Esto traerá id, nombre, direccion, activo, creado_en

class ModalidadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Modalidad
        fields = '__all__'
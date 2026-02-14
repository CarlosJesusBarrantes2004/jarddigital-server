from rest_framework import serializers
from .models import Departamento, Provincia, Distrito

class DepartamentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Departamento
        fields = ['id', 'codigo_ubigeo', 'nombre']

class ProvinciaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Provincia
        fields = ['id', 'id_departamento', 'codigo_ubigeo', 'nombre']

class DistritoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Distrito
        fields = ['id', 'id_provincia', 'codigo_ubigeo', 'nombre']
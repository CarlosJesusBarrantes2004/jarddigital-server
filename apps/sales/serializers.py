from rest_framework import serializers
from .models import Producto, TipoDocumento

class ProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = ['id', 'nombre_plan', 'es_alto_valor', 'costo_fijo_plan']

class TipoDocumentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoDocumento
        fields = ['id', 'codigo', 'nombre', 'longitud_exacta']
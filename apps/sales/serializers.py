from rest_framework import serializers
from .models import Producto

class ProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = ['id', 'nombre_plan', 'es_alto_valor', 'costo_fijo_plan']

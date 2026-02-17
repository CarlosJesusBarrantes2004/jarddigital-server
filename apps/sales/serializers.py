from rest_framework import serializers
from .models import EstadoSOT, SubEstadoSOT, EstadoAudio, Producto, GrabadorAudio

# ==========================================
# 1. CATÁLOGOS Y ESTADOS (Fase 1)
# ==========================================

class EstadoSOTSerializer(serializers.ModelSerializer):
    class Meta:
        model = EstadoSOT
        fields = ['id', 'codigo', 'nombre', 'orden', 'es_final', 'color_hex', 'activo']


class SubEstadoSOTSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubEstadoSOT
        fields = ['id', 'nombre', 'color_hex', 'requiere_nueva_fecha', 'activo']


class EstadoAudioSerializer(serializers.ModelSerializer):
    class Meta:
        model = EstadoAudio
        fields = ['id', 'codigo', 'nombre', 'activo']


# ==========================================
# 2. OPERATIVOS Y PRODUCTOS (Fase 2)
# ==========================================

class ProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = [
            'id',
            'nombre_plan',
            'es_alto_valor',
            'costo_fijo_plan',
            'comision_base',
            'fecha_inicio_vigencia',
            'fecha_fin_vigencia',
            'activo'
        ]


class GrabadorAudioSerializer(serializers.ModelSerializer):
    class Meta:
        model = GrabadorAudio
        fields = ['id', 'id_usuario', 'nombre_completo', 'activo']

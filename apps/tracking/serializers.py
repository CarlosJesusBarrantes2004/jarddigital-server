from rest_framework import serializers
from .models import Seguimiento, SeguimientoMensual
from apps.sales.serializers import VentaSerializer

class VentaParaSeguimientoSerializer(VentaSerializer):
    """
    Hereda TODO del VentaSerializer original, pero anulamos
    los audios anidados para que el JSON no pese una tonelada.
    """
    # Excelente truco: DRF ignorará este campo en la renderización
    audios = None

    class Meta(VentaSerializer.Meta):
        pass

class SeguimientoMensualSerializer(serializers.ModelSerializer):
    class Meta:
        model = SeguimientoMensual
        fields = [
            'id', 'mes_numero', 'pago_cliente_realizado',
            'fecha_seguimiento', 'fecha_validacion_pago',
            'observacion', 'conformidad', 'activo'
        ]
        read_only_fields = ['id', 'mes_numero']

class SeguimientoSerializer(serializers.ModelSerializer):
    meses_evaluados = SeguimientoMensualSerializer(many=True, read_only=True)
    venta = VentaParaSeguimientoSerializer(source='id_venta', read_only=True)

    class Meta:
        model = Seguimiento
        fields = [
            'id', 'venta', 'codigo_pago', 'ciclo_facturacion',
            'fecha_inicio', 'estado', 'descuento_realizado',
            'meses_evaluados', 'activo'
        ]
        # Eliminamos 'id_venta' de aquí. El serializador 'venta' ya es read_only=True por defecto.
        read_only_fields = ['id']
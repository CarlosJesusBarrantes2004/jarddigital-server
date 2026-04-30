from rest_framework import serializers
from .models import Seguimiento, SeguimientoMensual


class SeguimientoMensualSerializer(serializers.ModelSerializer):
    class Meta:
        model = SeguimientoMensual
        # Exponemos todos los campos útiles. 'id_seguimiento' no es necesario
        # enviarlo porque va implícito en la URL o en el objeto padre.
        fields = [
            'id', 'mes_numero', 'pago_cliente_realizado',
            'fecha_seguimiento', 'fecha_validacion_pago',
            'observacion', 'conformidad', 'activo'
        ]
        read_only_fields = ['id', 'mes_numero', 'fecha_seguimiento', 'fecha_validacion_pago']


class SeguimientoSerializer(serializers.ModelSerializer):
    # Anidamos los meses usando el related_name que definimos en el modelo
    meses_evaluados = SeguimientoMensualSerializer(many=True, read_only=True)

    # Datos de solo lectura que vienen de la Venta (para comodidad del frontend)
    codigo_sot = serializers.CharField(source='id_venta.codigo_sot', read_only=True)
    cliente_nombre = serializers.CharField(source='id_venta.cliente_nombre', read_only=True)

    class Meta:
        model = Seguimiento
        fields = [
            'id', 'id_venta', 'codigo_sot', 'cliente_nombre', 'codigo_pago',
            'ciclo_facturacion', 'fecha_inicio', 'estado',
            'descuento_realizado', 'meses_evaluados'
        ]
        read_only_fields = ['id', 'id_venta', 'ciclo_facturacion']
from rest_framework import serializers
from .models import Sucursal, Modalidad, TipoDocumento, ModalidadSede

class SucursalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sucursal
        fields = '__all__'  # Esto traerá id, nombre, direccion, activo, creado_en

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

    def get_etiqueta(self, obj):
        # Esto devolverá algo como: "Sede Principal Chiclayo - CALL CENTER"
        return f"{obj.id_sucursal.nombre} - {obj.id_modalidad.nombre}"
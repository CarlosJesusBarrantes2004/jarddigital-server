from rest_framework import serializers
from .models import Asistencia, ReglaComision, HistoricoPlanilla
from apps.users.models import Usuario  # Ajusta la ruta según tu proyecto


class AsistenciaLecturaSerializer(serializers.ModelSerializer):
    nombre_asesor = serializers.CharField(source='id_usuario.nombre_completo', read_only=True)

    # OPCIONAL: Si quieres que el frontend también reciba el nombre de la sucursal
    # nombre_sucursal = serializers.CharField(source='id_sucursal.nombre', read_only=True)

    class Meta:
        model = Asistencia
        fields = ['id', 'id_usuario', 'nombre_asesor', 'id_sucursal', 'fecha', 'asistio']


class AsistenciaUpsertSerializer(serializers.Serializer):
    # Validamos que el ID exista realmente en la BD
    id_usuario = serializers.PrimaryKeyRelatedField(queryset=Usuario.objects.all())
    fecha = serializers.DateField()

    # FIX 3: Retirado el default=None para evitar sobreescrituras silenciosas.
    # required=False permite que la llave no venga en el JSON.
    # allow_null=True permite enviar explícitamente "asistio": null.
    asistio = serializers.BooleanField(allow_null=True, required=False)


class ReglaComisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReglaComision
        # FIX 1: Listado explícito de campos en lugar de '__all__'
        fields = [
            'id', 'periodo_inicio', 'escenario',
            'min_ventas_pagadas_medio', 'min_ventas_pagadas_optimo',
            'alto_valor_nivel_1', 'alto_valor_nivel_2', 'alto_valor_nivel_3',
            'sueldo_base_elite', 'activo', 'creado_en'
        ]
        # Protegemos el ID y la fecha de creación contra inyecciones
        read_only_fields = ['id', 'creado_en']


class HistoricoPlanillaSerializer(serializers.ModelSerializer):
    nombre_asesor = serializers.CharField(source='id_usuario.nombre_completo', read_only=True)
    nombre_rrhh = serializers.CharField(source='procesado_por.nombre_completo', read_only=True)

    class Meta:
        model = HistoricoPlanilla
        # FIX 2 y 5: Listado explícito en fields y read_only_fields
        fields = [
            'id', 'id_usuario', 'nombre_asesor', 'mes_fiscal', 'anio_fiscal',
            'ventas_instaladas_mes_actual', 'ventas_pagadas_mes_anterior',
            'ventas_alto_valor_pagadas', 'cantidad_faltas', 'sueldo_base_aplicado',
            'porcentaje_pozo_aplicado', 'multiplicador_alto_valor',
            'pozo_comisiones_bruto', 'comision_neta_ganada', 'descuento_inasistencias',
            'sueldo_neto_final', 'fecha_liquidacion', 'procesado_por', 'nombre_rrhh'
        ]

        # Bloqueo total: Todo el modelo es estrictamente de lectura
        read_only_fields = [
            'id', 'id_usuario', 'mes_fiscal', 'anio_fiscal',
            'ventas_instaladas_mes_actual', 'ventas_pagadas_mes_anterior',
            'ventas_alto_valor_pagadas', 'cantidad_faltas', 'sueldo_base_aplicado',
            'porcentaje_pozo_aplicado', 'multiplicador_alto_valor',
            'pozo_comisiones_bruto', 'comision_neta_ganada', 'descuento_inasistencias',
            'sueldo_neto_final', 'fecha_liquidacion', 'procesado_por'
        ]
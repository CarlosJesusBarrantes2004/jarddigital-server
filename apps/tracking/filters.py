import django_filters
from .models import Seguimiento


class SeguimientoFilter(django_filters.FilterSet):
    # --- Filtros Globales ---
    es_alto_valor = django_filters.BooleanFilter(field_name="id_venta__id_producto__es_alto_valor")
    estado = django_filters.CharFilter(field_name="estado", lookup_expr="iexact")
    descuento_realizado = django_filters.BooleanFilter(field_name="descuento_realizado")

    # --- Filtros de Asesor / Venta ---
    mes_instalacion = django_filters.NumberFilter(field_name="id_venta__fecha_real_inst", lookup_expr="month")
    anio_instalacion = django_filters.NumberFilter(field_name="id_venta__fecha_real_inst", lookup_expr="year")

    # Validación Rápida: Indicador de si el primer mes está pagado
    primer_mes_pagado = django_filters.BooleanFilter(method='filter_primer_mes_pagado')

    # ==============================================================
    # ---> NUEVOS FILTROS SOLICITADOS <---
    # ==============================================================

    # 1. Filtro de Género (Cruza hacia la Venta)
    genero = django_filters.CharFilter(
        field_name="id_venta__cliente_genero",
        lookup_expr="istartswith"  # Permite ?genero=M o ?genero=F
    )

    # 2. Rango de Fechas de Validación de PAGO (Revisa los 6 meses hijos)
    # distinct=True es CRUCIAL para no duplicar el Seguimiento si varios meses coinciden
    fecha_pago_desde = django_filters.DateFilter(
        field_name="meses_evaluados__fecha_validacion_pago",
        lookup_expr='gte',
        distinct=True
    )
    fecha_pago_hasta = django_filters.DateFilter(
        field_name="meses_evaluados__fecha_validacion_pago",
        lookup_expr='lte',
        distinct=True
    )

    # 3. Rango de Fechas de SEGUIMIENTO (Revisa los 6 meses hijos)
    fecha_seguimiento_desde = django_filters.DateFilter(
        field_name="meses_evaluados__fecha_seguimiento",
        lookup_expr='gte',
        distinct=True
    )
    fecha_seguimiento_hasta = django_filters.DateFilter(
        field_name="meses_evaluados__fecha_seguimiento",
        lookup_expr='lte',
        distinct=True
    )

    def filter_primer_mes_pagado(self, queryset, name, value):
        """
        Atraviesa la relación inversa para verificar si el Mes 1 tiene
        el pago_cliente_realizado igual al booleano enviado en la URL.
        """
        return queryset.filter(
            meses_evaluados__mes_numero=1,
            meses_evaluados__pago_cliente_realizado=value
        )

    class Meta:
        model = Seguimiento
        fields = [
            'es_alto_valor', 'estado', 'descuento_realizado',
            'mes_instalacion', 'anio_instalacion'
        ]
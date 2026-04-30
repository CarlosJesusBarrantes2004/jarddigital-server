import django_filters
from .models import Seguimiento


class SeguimientoFilter(django_filters.FilterSet):
    # --- Filtros Globales ---
    # Filtrar ventas con es_alto_valor: true cruzando con Producto
    # (Nota: Asegúrate de que 'es_alto_valor' sea el nombre real en tu modelo Producto)
    es_alto_valor = django_filters.BooleanFilter(field_name="id_venta__id_producto__es_alto_valor")

    # Búsqueda exacta por PENALIZADO, SUSPENDIDO o DESACTIVADO
    estado = django_filters.CharFilter(field_name="estado", lookup_expr="iexact")

    # Filtrar por valores booleanos en descuento_realizado
    descuento_realizado = django_filters.BooleanFilter(field_name="descuento_realizado")

    # --- Filtros de Asesor ---
    # Mes donde la venta pasó a ATENDIDO (usamos fecha_real_inst de la Venta)
    mes_instalacion = django_filters.NumberFilter(field_name="id_venta__fecha_real_inst", lookup_expr="month")
    anio_instalacion = django_filters.NumberFilter(field_name="id_venta__fecha_real_inst", lookup_expr="year")

    # Validación Rápida: Indicador de si el primer mes está pagado
    primer_mes_pagado = django_filters.BooleanFilter(method='filter_primer_mes_pagado')

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
        fields = ['es_alto_valor', 'estado', 'descuento_realizado', 'mes_instalacion', 'anio_instalacion']
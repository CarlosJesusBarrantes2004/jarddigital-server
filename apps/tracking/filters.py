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
    primer_mes_pagado = django_filters.BooleanFilter(method='filter_primer_mes_pagado')

    # ==============================================================
    # ---> NUEVOS FILTROS SOLICITADOS (CORREGIDOS) <---
    # ==============================================================

    # 1. Filtro de Género
    genero = django_filters.CharFilter(
        field_name="id_venta__cliente_genero",
        lookup_expr="istartswith"
    )

    # 2. Rango de Fechas de Validación de PAGO
    # Usamos métodos personalizados para obligar a Django a buscar en el MISMO mes
    fecha_pago_desde = django_filters.DateFilter(method='filter_rango_pago')
    fecha_pago_hasta = django_filters.DateFilter(method='filter_rango_pago')

    # 3. Rango de Fechas de SEGUIMIENTO
    fecha_seguimiento_desde = django_filters.DateFilter(method='filter_rango_seguimiento')
    fecha_seguimiento_hasta = django_filters.DateFilter(method='filter_rango_seguimiento')

    # --- LÓGICA DE LOS MÉTODOS DE RANGO ---

    def filter_rango_pago(self, queryset, name, value):
        desde = self.data.get('fecha_pago_desde')
        hasta = self.data.get('fecha_pago_hasta')

        # Si mandaron ambos parámetros, este método se llamará dos veces.
        # Bloqueamos la segunda ejecución para no hacer trabajo doble.
        if name == 'fecha_pago_hasta' and desde:
            return queryset

        filtros = {}
        if desde: filtros['meses_evaluados__fecha_validacion_pago__gte'] = desde
        if hasta: filtros['meses_evaluados__fecha_validacion_pago__lte'] = hasta

        # ¡LA MAGIA! Al poner ambos parámetros en un solo .filter(),
        # Django hace un INNER JOIN estricto sobre la MISMA fila hija.
        return queryset.filter(**filtros).distinct()

    def filter_rango_seguimiento(self, queryset, name, value):
        desde = self.data.get('fecha_seguimiento_desde')
        hasta = self.data.get('fecha_seguimiento_hasta')

        if name == 'fecha_seguimiento_hasta' and desde:
            return queryset

        filtros = {}
        if desde: filtros['meses_evaluados__fecha_seguimiento__gte'] = desde
        if hasta: filtros['meses_evaluados__fecha_seguimiento__lte'] = hasta

        return queryset.filter(**filtros).distinct()

    def filter_primer_mes_pagado(self, queryset, name, value):
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
import django_filters
from .models import Venta


class VentaFilter(django_filters.FilterSet):
    # ---> FIX #5: Filtros de fecha de Claude <---
    # (Cambia 'fecha_creacion__date' por 'fecha_venta' si prefieres filtrar por la fecha real de la venta)
    fecha_inicio = django_filters.DateFilter(
        field_name="fecha_creacion__date",
        lookup_expr="gte",
    )
    fecha_fin = django_filters.DateFilter(
        field_name="fecha_creacion__date",
        lookup_expr="lte",
    )

    # Filtro normal por ID de estado
    id_estado_sot = django_filters.NumberFilter(field_name="id_estado_sot")

    # ← CLAVE: permite ?id_estado_sot__isnull=true para ventas PENDIENTES
    id_estado_sot__isnull = django_filters.BooleanFilter(
        field_name="id_estado_sot", lookup_expr="isnull"
    )

    id_sub_estado_sot = django_filters.NumberFilter(field_name="id_sub_estado_sot")
    id_estado_audios = django_filters.NumberFilter(field_name="id_estado_audios")
    id_producto = django_filters.NumberFilter(field_name="id_producto")
    id_origen_venta = django_filters.NumberFilter(field_name="id_origen_venta")
    id_sucursal = django_filters.NumberFilter(field_name="id_origen_venta__id_sucursal")
    id_modalidad = django_filters.NumberFilter(
        field_name="id_origen_venta__id_modalidad"
    )
    tecnologia = django_filters.CharFilter(
        field_name="tecnologia", lookup_expr="iexact"
    )
    es_full_claro = django_filters.BooleanFilter(field_name="es_full_claro")

    # ← CLAVE: permite ?solicitud_correccion=true para ventas EN CORRECCIÓN
    solicitud_correccion = django_filters.BooleanFilter(
        field_name="solicitud_correccion"
    )

    class Meta:
        model = Venta
        fields = [
            "fecha_inicio",  # Añadido por orden visual
            "fecha_fin",  # Añadido por orden visual
            "id_estado_sot",
            "id_sub_estado_sot",
            "id_estado_audios",
            "id_producto",
            "id_origen_venta",
            "id_sucursal",
            "id_modalidad",
            "tecnologia",
            "es_full_claro",
            "solicitud_correccion",
        ]

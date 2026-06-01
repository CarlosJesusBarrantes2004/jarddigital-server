import django_filters
from .models import Asistencia

class AsistenciaFilter(django_filters.FilterSet):
    mes = django_filters.NumberFilter(field_name="fecha", lookup_expr="month")
    anio = django_filters.NumberFilter(field_name="fecha", lookup_expr="year")
    id_usuario = django_filters.NumberFilter(field_name="id_usuario_id")
    id_sucursal = django_filters.NumberFilter(field_name="id_sucursal_id")

    # --->FILTRO: Por SEDE-MODALIDAD <---
    modalidad_sede = django_filters.NumberFilter(
        field_name="id_usuario__permisos__id_modalidad_sede",
        distinct=True
    )

    # --->FILTRO: Por Código de Rol <---
    rol = django_filters.CharFilter(
        field_name="id_usuario__id_rol__codigo",
        lookup_expr="iexact"
    )

    class Meta:
        model = Asistencia
        fields = ['mes', 'anio', 'id_usuario', 'id_sucursal', 'asistio', 'modalidad_sede', 'rol']
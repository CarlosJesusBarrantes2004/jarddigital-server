from rest_framework import viewsets
from drf_spectacular.utils import extend_schema, OpenApiParameter
from .models import Departamento, Provincia, Distrito
from .serializers import DepartamentoSerializer, ProvinciaSerializer, DistritoSerializer

class DepartamentoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Lista todos los departamentos del Perú. Solo lectura.
    """
    queryset = Departamento.objects.all()
    serializer_class = DepartamentoSerializer


class ProvinciaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Lista las provincias. Permite filtrar por id_departamento.
    """
    serializer_class = ProvinciaSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(name="id_departamento", description="Filtrar provincias por ID de Departamento", required=False, type=int),
        ]
    )
    def get_queryset(self):
        queryset = Provincia.objects.all()
        # Si el frontend envía el parámetro ?id_departamento=X, filtramos la lista
        id_departamento = self.request.query_params.get('id_departamento', None)
        if id_departamento is not None:
            queryset = queryset.filter(id_departamento=id_departamento)
        return queryset


class DistritoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Lista los distritos. Permite filtrar por id_provincia.
    """
    serializer_class = DistritoSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(name="id_provincia", description="Filtrar distritos por ID de Provincia", required=False, type=int),
        ]
    )
    def get_queryset(self):
        queryset = Distrito.objects.all()
        # Si el frontend envía el parámetro ?id_provincia=Y, filtramos la lista
        id_provincia = self.request.query_params.get('id_provincia', None)
        if id_provincia is not None:
            queryset = queryset.filter(id_provincia=id_provincia)
        return queryset
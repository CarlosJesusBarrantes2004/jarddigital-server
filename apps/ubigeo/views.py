from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
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
    Lista las provincias. Permite filtrar por id_departamento en cascada.
    """
    queryset = Provincia.objects.all()
    serializer_class = ProvinciaSerializer

    # 1. Activamos el motor de filtros exactos
    filter_backends = [DjangoFilterBackend]
    # 2. Le decimos por qué campo (exactamente como se llama en tu modelo) se puede filtrar
    filterset_fields = ['id_departamento']


class DistritoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Lista los distritos. Permite filtrar por id_provincia en cascada.
    """
    queryset = Distrito.objects.all()
    serializer_class = DistritoSerializer

    # Repetimos la magia para los distritos
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['id_provincia']
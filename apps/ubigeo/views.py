from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from .models import Departamento, Provincia, Distrito
from .serializers import DepartamentoSerializer, ProvinciaSerializer, DistritoSerializer

# Tiempo de caché: 24 horas (60 segundos * 60 minutos * 24 horas)
TIEMPO_CACHE = 60 * 60 * 24

class DepartamentoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Lista todos los departamentos del Perú.
    Cacheado por 24 horas y sin paginación.
    """
    queryset = Departamento.objects.all()
    serializer_class = DepartamentoSerializer
    permission_classes = [IsAuthenticated]

    # 1. Bypass del paginador global (Devuelve la lista completa siempre)
    pagination_class = None

    # 2. Guardamos la respuesta en RAM para rendimiento extremo
    @method_decorator(cache_page(TIEMPO_CACHE))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


class ProvinciaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Lista las provincias. Permite filtrar por id_departamento.
    """
    queryset = Provincia.objects.all()
    serializer_class = ProvinciaSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['id_departamento']

    pagination_class = None # Bypass de paginación

    # El caché es inteligente: guardará en RAM resultados separados
    # para cada filtro (ej. guardará en memoria "?id_departamento=1" distinto de "?id_departamento=2")
    @method_decorator(cache_page(TIEMPO_CACHE))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


class DistritoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Lista los distritos. Permite filtrar por id_provincia.
    """
    queryset = Distrito.objects.all()
    serializer_class = DistritoSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['id_provincia']

    pagination_class = None # Bypass de paginación (¡Salvamos a Lima y sus 43 distritos!)

    @method_decorator(cache_page(TIEMPO_CACHE))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
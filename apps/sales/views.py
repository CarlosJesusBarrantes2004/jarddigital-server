from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

# Importamos tu papelera de reciclaje y tus aduanas
from apps.core.mixins import SoftDeleteModelViewSet
from apps.users.permissions import SoloLecturaOCrearSiEsJefe

from .models import EstadoSOT, SubEstadoSOT, EstadoAudio, Producto, GrabadorAudio
from .serializers import (
    EstadoSOTSerializer,
    SubEstadoSOTSerializer,
    EstadoAudioSerializer,
    ProductoSerializer,
    GrabadorAudioSerializer
)


# ==========================================
# 1. CATÁLOGOS Y ESTADOS (Fase 1)
# ==========================================

class EstadoSOTViewSet(SoftDeleteModelViewSet):
    # Usamos order_by('orden') para que el frontend los pinte en el orden lógico del negocio
    queryset = EstadoSOT.objects.all().order_by('orden')
    serializer_class = EstadoSOTSerializer
    permission_classes = [IsAuthenticated, SoloLecturaOCrearSiEsJefe]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['nombre', 'codigo']


class SubEstadoSOTViewSet(SoftDeleteModelViewSet):
    queryset = SubEstadoSOT.objects.all()
    serializer_class = SubEstadoSOTSerializer
    permission_classes = [IsAuthenticated, SoloLecturaOCrearSiEsJefe]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['nombre']


class EstadoAudioViewSet(SoftDeleteModelViewSet):
    queryset = EstadoAudio.objects.all()
    serializer_class = EstadoAudioSerializer
    permission_classes = [IsAuthenticated, SoloLecturaOCrearSiEsJefe]
    filter_backends = [filters.SearchFilter]
    search_fields = ['nombre', 'codigo']


# ==========================================
# 2. OPERATIVOS Y PRODUCTOS (Fase 2)
# ==========================================

class ProductoViewSet(SoftDeleteModelViewSet):
    # Ordenamos por los más recientes primero
    queryset = Producto.objects.all().order_by('-fecha_inicio_vigencia')
    serializer_class = ProductoSerializer
    permission_classes = [IsAuthenticated, SoloLecturaOCrearSiEsJefe]

    # Activamos los filtros para que el asesor pueda buscar rápido su plan
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['es_alto_valor']  # ?es_alto_valor=True
    search_fields = ['nombre_plan']  # ?search=Max 29.90


class GrabadorAudioViewSet(SoftDeleteModelViewSet):
    # select_related preventivo por si a futuro el frontend pide datos del usuario vinculado
    queryset = GrabadorAudio.objects.select_related('id_usuario').all()
    serializer_class = GrabadorAudioSerializer
    permission_classes = [IsAuthenticated, SoloLecturaOCrearSiEsJefe]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['nombre_completo']

from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from apps.sales.models import Venta
from apps.sales.serializers import VentaSerializer
from django_filters.rest_framework import DjangoFilterBackend
from .filters import VentaFilter
from rest_framework.decorators import action

# Importamos tu papelera de reciclaje y tus aduanas
from apps.core.mixins import SoftDeleteModelViewSet
from apps.users.permissions import SoloLecturaOCrearSiEsJefe
from apps.users.models import PermisoAcceso

from .selectors import obtener_ventas_permitidas
from .services import generar_excel_ventas
from .selectors import obtener_grabadores_disponibles
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
    filterset_fields = ['es_alto_valor', 'nombre_campana', 'tipo_solucion', 'activo']  # ?es_alto_valor=True
    search_fields = ['nombre_paquete', 'nombre_campana']  # ?search=Max 29.90


class GrabadorAudioViewSet(viewsets.ReadOnlyModelViewSet):
    # El queryset base (trae todos)
    queryset = GrabadorAudio.objects.select_related('id_usuario').filter(activo=True).order_by('id')
    serializer_class = GrabadorAudioSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['activo']
    search_fields = ['nombre_completo']

    def get_queryset(self):
        queryset = super().get_queryset()

        if self.action == 'list':
            # 1. Capturamos si el frontend está editando una venta (ej: ?id_venta_actual=15)
            id_venta_actual = self.request.query_params.get('id_venta_actual')

            # 2. Le pasamos ese ID al selector
            queryset = obtener_grabadores_disponibles(
                queryset_base=queryset,
                id_venta_actual=id_venta_actual
            )

        return queryset


# ==========================================
# 3. LA BESTIA: VENTAS (CORE)
# ==========================================

class VentaViewSet(SoftDeleteModelViewSet):
    serializer_class = VentaSerializer
    permission_classes = [IsAuthenticated]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = VentaFilter
    search_fields = ["cliente_numero_doc", "cliente_nombre", "codigo_sec", "codigo_sot", "id_asesor__nombre_completo"]
    ordering_fields = ['fecha_venta', 'fecha_creacion']
    ordering = ['-fecha_venta']

    def get_queryset(self):
        # 1. Delegamos toda la lógica de RLS y Joins al Selector
        return obtener_ventas_permitidas(self.request.user)

    @action(detail=False, methods=['get'])
    def exportar_excel(self, request):
        # 1. Recibimos parámetros
        fecha_inicio = request.query_params.get('fecha_inicio')
        fecha_fin = request.query_params.get('fecha_fin')
        estado_filtro = request.query_params.get('estado_sot')

        # 2. Delegamos la generación del Excel al Servicio
        return generar_excel_ventas(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            estado_filtro=estado_filtro,
            usuario_peticion=request.user  # ¡El candado!
        )
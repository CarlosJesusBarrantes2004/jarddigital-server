from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from apps.sales.models import Venta
from apps.sales.serializers import VentaSerializer
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone

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


class GrabadorAudioViewSet(viewsets.ReadOnlyModelViewSet):
    # El queryset base (trae todos)
    queryset = GrabadorAudio.objects.select_related('id_usuario').all().order_by('id')
    serializer_class = GrabadorAudioSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['nombre_completo']

    def get_queryset(self):
        # 1. Obtenemos la lista completa inicial
        queryset = super().get_queryset()

        # 2. Solo aplicamos la lógica de exclusión si estamos LISTANDO (para el dropdown)
        if self.action == 'list':
            hoy = timezone.now().date()

            # 3. Buscamos los grabadores que están "Ocupados" hoy.
            # REGLA: Ocupado = Tiene venta creada HOY y la venta está ACTIVA.
            # (Esto bloquea Rechazados, Pendientes, etc. Solo libera si activo=False es decir ANULADA)
            ids_bloqueados = Venta.objects.filter(
                fecha_creacion__date=hoy,
                activo=True
            ).exclude(
                # REGLA DE ORO: El ID 1 (OTROS) NUNCA entra en la lista negra.
                # Aunque tenga 1000 ventas activas hoy, lo sacamos de la lista de bloqueados.
                id_grabador_audios=1
            ).values_list('id_grabador_audios', flat=True)

            # 4. Excluimos los IDs bloqueados de la respuesta final
            if ids_bloqueados:
                queryset = queryset.exclude(id__in=ids_bloqueados)

        return queryset


# ==========================================
# 3. LA BESTIA: VENTAS (CORE)
# ==========================================

class VentaViewSet(SoftDeleteModelViewSet):
    serializer_class = VentaSerializer
    permission_classes = [IsAuthenticated]  # Todos deben estar logueados

    # Activamos los motores de búsqueda, filtros y ordenamiento
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    # 1. Filtros exactos para los combos del Backoffice
    filterset_fields = [
        'id_estado_sot',
        'id_sub_estado_sot',
        'id_estado_audios',
        'id_producto',
        'id_origen_venta',
        'tecnologia',
        'es_full_claro'
    ]

    # 2. Buscador libre (Para cuando el cliente llama reclamando y solo dan su DNI)
    search_fields = [
        'cliente_numero_doc',
        'cliente_nombre',
        'codigo_sec',
        'codigo_sot'
    ]

    # 3. Ordenamiento (Por defecto, las ventas más nuevas arriba)
    ordering_fields = ['fecha_venta', 'fecha_creacion']
    ordering = ['-fecha_venta']

    def get_queryset(self):
        user = self.request.user

        # ==========================================
        # FASE 1: OPTIMIZACIÓN EXTREMA (SQL JOINs)
        # ==========================================
        # Hacemos un JOIN masivo para que Django no haga consultas extra por cada llave foránea
        queryset = Venta.objects.select_related(
            'id_asesor',
            'id_origen_venta__id_sucursal',
            'id_origen_venta__id_modalidad',
            'id_supervisor_vigente__id_supervisor',
            'id_producto',
            'id_tipo_documento',
            'id_distrito_nacimiento',
            'id_distrito_instalacion',
            'id_sub_estado_sot',
            'id_estado_sot',
            'id_grabador_audios',
            'id_estado_audios',
            'usuario_revision_audios',
            'venta_origen'
        ).all()

        # ==========================================
        # FASE 2: SEGURIDAD DE DATOS (Tenant Isolation)
        # ==========================================
        # Verificamos qué tipo de usuario está pidiendo los datos
        if hasattr(user, 'id_rol') and user.id_rol:

            # Si es un ASESOR, le ponemos un candado: Solo ve sus propias ventas
            if user.id_rol.codigo == 'ASESOR':
                queryset = queryset.filter(id_asesor=user)

            # Si es SUPERVISOR, solo ve las ventas de sus sedes asignadas
            elif user.id_rol.codigo == 'SUPERVISOR':
                sedes_supervisadas = user.asignaciones_supervisor.filter(
                    activo=True,
                    fecha_fin__isnull=True
                ).values_list('id_modalidad_sede', flat=True)

                queryset = queryset.filter(id_origen_venta__in=sedes_supervisadas)

            # Si es BACKOFFICE o DUENO, el if los ignora y ven el queryset completo.

        return queryset
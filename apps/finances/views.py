import logging
from rest_framework import mixins
from apps.core.models import Sucursal
from .filters import AsistenciaFilter
from .selectors import obtener_asistencias_optimizadas
from .serializers import AsistenciaLecturaSerializer, AsistenciaUpsertSerializer
from .services import upsert_asistencia_masiva
from .services import generar_excel_asistencias_mensual

from datetime import date
from django.core.cache import cache
from rest_framework import viewsets, views, status, serializers
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend

# Importamos modelos y serializers
from .models import ReglaComision
from .serializers import ReglaComisionSerializer, HistoricoPlanillaSerializer

# Importamos los servicios y selectores
from .services import liquidar_planilla_mensual, proyectar_comisiones_asesor
from .selectors import obtener_planillas_mensuales_optimizadas

# Importamos tus permisos
from apps.users.permissions import EsDueño, PuedeTomarAsistencia

# Configuración del Logger para producción
logger = logging.getLogger(__name__)


class AsistenciaViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    ViewSet para cargar y guardar la grilla mensual de asistencias.
    """
    permission_classes = [IsAuthenticated, PuedeTomarAsistencia]
    filter_backends = [DjangoFilterBackend]
    filterset_class = AsistenciaFilter

    @action(detail=False, methods=['GET'])
    def exportar_excel(self, request):
        # 1. Filtramos el queryset con tu método base
        queryset = self.filter_queryset(self.get_queryset())

        # 2. Identificamos qué mes y año estamos procesando (para dibujar las columnas)
        mes_str = request.query_params.get('mes')
        anio_str = request.query_params.get('anio')

        hoy = date.today()
        mes = int(mes_str) if mes_str and mes_str.isdigit() else hoy.month
        anio = int(anio_str) if anio_str and anio_str.isdigit() else hoy.year

        # 3. Delegamos el procesamiento y entregamos el archivo
        return generar_excel_asistencias_mensual(queryset, mes, anio)

    def get_queryset(self):
        # 1. Obtenemos la base optimizada
        queryset = obtener_asistencias_optimizadas()

        # 2. Capturamos lo que el frontend nos está pidiendo en la URL
        mes = self.request.query_params.get('mes')
        anio = self.request.query_params.get('anio')

        # 3. ESCUDO PROTECTOR: Si no mandan filtros, forzamos el mes actual
        if not mes or not anio:
            hoy = date.today()
            queryset = queryset.filter(fecha__month=hoy.month, fecha__year=hoy.year)

        return queryset

    def get_serializer_class(self):
        return AsistenciaLecturaSerializer

    @action(detail=False, methods=['POST'])
    def guardado_masivo(self, request):
        id_sucursal = request.data.get('id_sucursal')

        # Validación estricta del Punto 2
        if not str(id_sucursal).isdigit() or not Sucursal.objects.filter(id=id_sucursal).exists():
            return Response(
                {"error": "El id_sucursal es inválido o no existe."},
                status=status.HTTP_400_BAD_REQUEST
            )

        lista_asistencias = request.data.get('asistencias', [])
        serializer = AsistenciaUpsertSerializer(data=lista_asistencias, many=True)
        serializer.is_valid(raise_exception=True)

        procesados = upsert_asistencia_masiva(
            datos_validados=serializer.validated_data,
            id_sucursal=id_sucursal,
            usuario_peticion=request.user
        )

        return Response({
            "mensaje": f"Se procesaron {procesados} registros exitosamente."
        }, status=status.HTTP_200_OK)


# ==========================================
# SERIALIZADOR DE VALIDACIÓN DE ENTRADA
# ==========================================
class PeriodoInputSerializer(serializers.Serializer):
    mes = serializers.IntegerField(min_value=1, max_value=12)
    anio = serializers.IntegerField(min_value=2020, max_value=2100)


# ==========================================
# VISTAS DE LA API
# ==========================================
class ReglaComisionViewSet(viewsets.ModelViewSet):
    """
    ENDPOINT 1: CRUD para que el Dueño configure los umbrales financieros.
    La paginación se hereda de la configuración global (DEFAULT_PAGINATION_CLASS).
    """
    queryset = ReglaComision.objects.all().order_by('-periodo_inicio')
    serializer_class = ReglaComisionSerializer
    permission_classes = [IsAuthenticated, EsDueño]


class LiquidacionRRHHViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ENDPOINT 2: Mesa de Control para Recursos Humanos.
    """
    serializer_class = HistoricoPlanillaSerializer
    permission_classes = [IsAuthenticated, PuedeTomarAsistencia]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['mes_fiscal', 'anio_fiscal', 'id_usuario']

    def get_queryset(self):
        return obtener_planillas_mensuales_optimizadas()

    @action(detail=False, methods=['POST'])
    def ejecutar_liquidacion(self, request):
        """
        Botón de pánico de RRHH: Ejecuta el cálculo masivo de toda la empresa.
        Retorna HTTP 200 OK de manera semántica al utilizar update_or_create.
        """
        # Validación estricta de entrada
        serializer = PeriodoInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        mes = serializer.validated_data['mes']
        anio = serializer.validated_data['anio']

        # Bloqueo de Concurrencia (Mutex Lock en Caché - 60 segundos)
        lock_key = f"lock_liquidacion_masiva_{mes}_{anio}"
        if not cache.add(lock_key, "locked", 60):
            return Response(
                {"error": "Ya existe un proceso de liquidación ejecutándose para este periodo. Por favor, espere."},
                status=status.HTTP_409_CONFLICT
            )

        try:
            resultado = liquidar_planilla_mensual(mes, anio, request.user)
            return Response(resultado, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error crítico en liquidación masiva ({mes}/{anio}): {str(e)}", exc_info=True)
            return Response(
                {
                    "error": "Ocurrió un error interno al procesar las liquidaciones. El equipo técnico ha sido notificado."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        finally:
            # Liberamos el candado al terminar, falle o no
            cache.delete(lock_key)


class MiDashboardFinancieroView(views.APIView):
    """
    ENDPOINT 3: Vista en vivo para que el Asesor vea cuánto dinero lleva ganado.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Guarda de Seguridad: Solo Asesores
        if not hasattr(request.user, 'id_rol') or request.user.id_rol.codigo != 'ASESOR':
            return Response(
                {"error": "Este panel financiero es exclusivo para los Asesores."},
                status=status.HTTP_403_FORBIDDEN
            )

        hoy = date.today()
        # Validación de Query Params
        data_entrada = {
            'mes': request.query_params.get('mes', hoy.month),
            'anio': request.query_params.get('anio', hoy.year)
        }

        serializer = PeriodoInputSerializer(data=data_entrada)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        mes = serializer.validated_data['mes']
        anio = serializer.validated_data['anio']

        try:
            proyeccion = proyectar_comisiones_asesor(request.user, mes, anio)
            return Response(proyeccion, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error en dashboard de asesor ID {request.user.id}: {str(e)}", exc_info=True)
            return Response(
                {"error": "No pudimos calcular tu proyección en este momento."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
from rest_framework import viewsets, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django_filters.rest_framework import DjangoFilterBackend

from apps.core.models import Sucursal
from datetime import date
from .filters import AsistenciaFilter
from .selectors import obtener_asistencias_optimizadas
from .serializers import AsistenciaLecturaSerializer, AsistenciaUpsertSerializer
from .services import upsert_asistencia_masiva
from .services import generar_excel_asistencias_mensual
from rest_framework.permissions import IsAuthenticated
from apps.users.permissions import PuedeTomarAsistencia

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
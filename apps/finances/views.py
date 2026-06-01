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

class AsistenciaViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    ViewSet para cargar y guardar la grilla mensual de asistencias.
    """
    filter_backends = [DjangoFilterBackend]
    filterset_class = AsistenciaFilter

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
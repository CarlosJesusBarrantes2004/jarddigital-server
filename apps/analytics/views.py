import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from apps.users.permissions import PuedeVerPlanillas
from .serializers import (
    MatrizPivoteInputSerializer,
    BarrasRendimientoInputSerializer,
    TendenciaDiariaInputSerializer,
    DistribucionJerarquicaInputSerializer
)
from .selectors import (
    obtener_matriz_pivote_sql,
    query_barras_rendimiento,
    obtener_tendencia_diaria,
    obtener_nivel_jerarquico
)

logger = logging.getLogger(__name__)


class MatrizRendimientoView(APIView):
    """Endpoint para Gráficos 1 y 3 (Tabla Pivote)"""
    permission_classes = [IsAuthenticated, PuedeVerPlanillas]

    def get(self, request):
        serializer = MatrizPivoteInputSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        datos = serializer.validated_data
        try:
            data = obtener_matriz_pivote_sql(
                anio=datos['anio'],
                estado_sot=datos['estado_sot']
            )
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error en matriz de rendimiento: {str(e)}", exc_info=True)
            return Response(
                {"error": "No se pudo generar la matriz de rendimiento."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BarrasRendimientoView(APIView):
    """Endpoint para Gráficos 2 y 4 (Gráficos de Barras)"""
    permission_classes = [IsAuthenticated, PuedeVerPlanillas]

    def get(self, request):
        serializer = BarrasRendimientoInputSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        datos = serializer.validated_data
        try:
            data = query_barras_rendimiento(
                anio=datos['anio'],
                estado_sot=datos.get('estado_sot'),
                mes=datos.get('mes'),
                id_asesor=datos.get('id_asesor')
            )
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error en barras de rendimiento: {str(e)}", exc_info=True)
            return Response(
                {"error": "No se pudo generar el gráfico de barras."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TendenciaDiariaView(APIView):
    """Endpoint para Gráfico 5 (Líneas comparativas día a día)"""
    permission_classes = [IsAuthenticated, PuedeVerPlanillas]

    def get(self, request):
        serializer = TendenciaDiariaInputSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        datos = serializer.validated_data
        try:
            data = obtener_tendencia_diaria(
                anio=datos['anio'],
                mes=datos['mes'],
                modalidad=datos.get('modalidad')
            )
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error en tendencia diaria: {str(e)}", exc_info=True)
            return Response(
                {"error": "No se pudo generar la tendencia diaria."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DistribucionJerarquicaView(APIView):
    """Endpoint para Gráfico 6 (Árbol Drill-down geográfico o producto)"""
    permission_classes = [IsAuthenticated, PuedeVerPlanillas]

    def get(self, request):
        serializer = DistribucionJerarquicaInputSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        datos = serializer.validated_data
        try:
            data = obtener_nivel_jerarquico(
                estado_sot=datos['estado_sot'],
                dimension=datos['dimension'],
                nivel=datos['nivel'],
                anio=datos.get('anio'),
                padre_id=datos.get('padre_id'),
                solo_alto_valor=datos.get('solo_alto_valor', False)
            )
            return Response(data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error en distribución jerárquica: {str(e)}", exc_info=True)
            return Response(
                {"error": "No se pudo generar la distribución jerárquica."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

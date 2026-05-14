from rest_framework import viewsets, mixins, status, filters
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend

# Modelos, serializadores y filtros
from .models import Seguimiento, SeguimientoMensual
from .serializers import SeguimientoSerializer, SeguimientoMensualSerializer
from .filters import SeguimientoFilter

# Servicios y Selectores (¡Aquí entra la magia!)
from .services import actualizar_seguimiento_mensual, recalcular_fechas_por_nuevo_ciclo, generar_excel_seguimiento_pendientes
from .selectors import obtener_seguimientos_optimizados

# Seguridad
from apps.users.permissions import PuedeGestionarSeguimiento


class SeguimientoViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """
    ViewSet para la Cabecera.
    Permite listar todos los seguimientos y ver el detalle de uno (con sus meses anidados).
    """
    serializer_class = SeguimientoSerializer
    permission_classes = [IsAuthenticated, PuedeGestionarSeguimiento]

    # ---> MOTORES DE BÚSQUEDA Y FILTROS ACTIVADOS <---
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = SeguimientoFilter
    search_fields = ["id_venta__codigo_sot", "id_venta__cliente_nombre", "codigo_pago"]
    ordering_fields = ['id_venta__fecha_real_inst', 'ciclo_facturacion']

    def get_queryset(self):
        # Delegamos toda la carga pesada y las anotaciones a nuestro selector optimizado
        return obtener_seguimientos_optimizados(self.request.user)

    def perform_update(self, serializer):
        instance = self.get_object()
        nuevo_ciclo = serializer.validated_data.get('ciclo_facturacion')

        # REGLA: Si envían un nuevo ciclo, es diferente al que ya tenía,
        # y el flag de "modificado manualmente" sigue en False.
        if (nuevo_ciclo and
                nuevo_ciclo != instance.ciclo_facturacion and
                not instance.ciclo_modificado_manualmente):

            # 1. Guardamos activando el flag oculto
            seguimiento_actualizado = serializer.save(ciclo_modificado_manualmente=True)

            # 2. Disparamos la cascada
            recalcular_fechas_por_nuevo_ciclo(seguimiento_actualizado, nuevo_ciclo)
        else:
            # Flujo normal para cualquier otra edición (ej. cambiar el estado)
            serializer.save()

    @action(detail=False, methods=['GET'])
    def exportar_pendientes_mes_1(self, request):
        """
        Endpoint: /api/tracking/seguimientos/exportar_pendientes_mes_1/
        Descarga el Excel con los clientes que deben el primer mes.
        """
        # Delegamos toda la lógica y seguridad a nuestro servicio
        return generar_excel_seguimiento_pendientes(usuario_peticion=request.user)


class SeguimientoMensualViewSet(mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """
    ViewSet Restringido para el Detalle (Meses).
    Hereda de GenericViewSet y UpdateModelMixin para SOLO permitir peticiones PUT/PATCH.
    No permite GET (list), POST (create) ni DELETE (destroy).
    """
    queryset = SeguimientoMensual.objects.filter(activo=True)
    serializer_class = SeguimientoMensualSerializer
    permission_classes = [IsAuthenticated, PuedeGestionarSeguimiento]

    def update(self, request, *args, **kwargs):
        """
        Sobrescribimos el método update para interceptar la data y mandarla a nuestro servicio.
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        # 1. Dejamos que el Serializer valide los tipos de datos básicos (fechas válidas, booleanos)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        # 2. Delegamos la bomba (Las Reglas de Negocio) a nuestro Servicio
        mes_actualizado = actualizar_seguimiento_mensual(
            mes_instance=instance,
            datos_validados=serializer.validated_data,
            usuario_peticion=request.user
        )

        # 3. Respondemos con el registro ya actualizado
        respuesta_serializer = self.get_serializer(mes_actualizado)
        return Response(respuesta_serializer.data, status=status.HTTP_200_OK)
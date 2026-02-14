from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .mixins import SoftDeleteModelViewSet # Importamos el superpoder
from .models import Sucursal, Modalidad, TipoDocumento, ModalidadSede
from .serializers import SucursalSerializer, ModalidadSerializer, TipoDocumentoSerializer, ModalidadSedeOpcionesSerializer

class SucursalViewSet(SoftDeleteModelViewSet):
    # ¡Importante! Aquí le pasamos .all() para que el mixin haga el trabajo sucio de filtrar
    queryset = Sucursal.objects.all()
    serializer_class = SucursalSerializer
    permission_classes = [IsAuthenticated]

class ModalidadViewSet(SoftDeleteModelViewSet):
    # Cambiamos el .filter() por .all() igual que arriba
    queryset = Modalidad.objects.all()
    serializer_class = ModalidadSerializer
    permission_classes = [IsAuthenticated]

class TipoDocumentoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Lista todos los tipos de documento activos (DNI, RUC, CE, etc.)
    """
    # Como este es ReadOnly (solo lectura), no borra ni edita nada.
    # Por lo tanto, NO necesita heredar nuestro SoftDeleteModelViewSet, se queda tal cual.
    queryset = TipoDocumento.objects.filter(activo=True)
    serializer_class = TipoDocumentoSerializer


class ModalidadSedeOpcionesViewSet(viewsets.ReadOnlyModelViewSet):
    """API para que el frontend llene sus combos de Sucursal+Modalidad"""
    queryset = ModalidadSede.objects.filter(
        activo=True,
        id_sucursal__activo=True,
        id_modalidad__activo=True
    ).select_related('id_sucursal', 'id_modalidad')

    serializer_class = ModalidadSedeOpcionesSerializer
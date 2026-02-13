from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Sucursal, Modalidad
from .serializers import SucursalSerializer, ModalidadSerializer

class SucursalViewSet(viewsets.ModelViewSet):
    # Solo listamos las sucursales que estén activas
    queryset = Sucursal.objects.filter(activo=True)
    serializer_class = SucursalSerializer
    permission_classes = [IsAuthenticated]

    # ¡LA MAGIA DEL SOFT DELETE!
    def destroy(self, request, *args, **kwargs):
        sucursal = self.get_object() # Obtenemos la sucursal a "borrar"
        sucursal.activo = False      # La apagamos
        sucursal.save()              # Guardamos el cambio
        return Response({"mensaje": "Sucursal desactivada correctamente"}, status=status.HTTP_204_NO_CONTENT)

class ModalidadViewSet(viewsets.ModelViewSet):
    queryset = Modalidad.objects.filter(activo=True)
    serializer_class = ModalidadSerializer
    permission_classes = [IsAuthenticated]

    def destroy(self, request, *args, **kwargs):
        modalidad = self.get_object()
        modalidad.activo = False
        modalidad.save()
        return Response({"mensaje": "Modalidad desactivada correctamente"}, status=status.HTTP_204_NO_CONTENT)

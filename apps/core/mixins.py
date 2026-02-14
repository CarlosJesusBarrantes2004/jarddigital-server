from rest_framework import viewsets, status
from rest_framework.response import Response


class SoftDeleteModelViewSet(viewsets.ModelViewSet):
    """
    Clase base inteligente para manejar el Borrado Lógico.
    Cualquier ViewSet que herede de aquí ganará estos métodos automáticamente.
    """

    def get_queryset(self):
        # 1. Traemos el queryset base (ej: Sucursal.objects.all())
        queryset = super().get_queryset()

        # 2. Si el frontend pide la lista completa, le damos solo los activos
        if self.action == 'list':
            return queryset.filter(activo=True)

        # 3. Si busca por ID (para ver, editar o restaurar), le permitimos encontrarlo
        return queryset

    def destroy(self, request, *args, **kwargs):
        # El engaño perfecto: apagamos en lugar de borrar
        instancia = self.get_object()
        instancia.activo = False
        instancia.save()
        return Response(
            {"mensaje": "Registro desactivado correctamente"},
            status=status.HTTP_204_NO_CONTENT
        )
from rest_framework import viewsets, status
from rest_framework.response import Response


class SoftDeleteModelViewSet(viewsets.ModelViewSet):
    """
    Clase base inteligente para manejar el Borrado Lógico y Filtrado de Estados.
    """

    def get_queryset(self):
        queryset = super().get_queryset()

        if self.action == 'list':
            # 1. Capturamos el parámetro de la URL (si no lo envían, es None)
            estado = self.request.query_params.get('estado', None)

            # 2. Comparamos y filtramos según lo que pida el frontend
            if estado == 'inactivo':
                return queryset.filter(activo=False)
            elif estado == 'todos':
                return queryset  # Devuelve la tabla completa sin filtros
            else:
                # Comportamiento por defecto: Mostrar solo los activos
                return queryset.filter(activo=True)

        # Si busca por ID (para ver, editar o restaurar), le permitimos encontrarlo siempre
        return queryset

    def destroy(self, request, *args, **kwargs):
        instancia = self.get_object()
        instancia.activo = False
        instancia.save()
        return Response(
            {"mensaje": "Registro desactivado correctamente"},
            status=status.HTTP_204_NO_CONTENT
        )
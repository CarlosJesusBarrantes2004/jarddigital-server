from rest_framework import viewsets, status
from rest_framework.response import Response

class SoftDeleteModelViewSet(viewsets.ModelViewSet):
    """
    Clase base inteligente para manejar el Borrado Lógico y Filtrado de Estados.
    Compatible con filtros nativos (?estado=inactivo) y django_filters (?activo=false).
    """

    def get_queryset(self):
        queryset = super().get_queryset()

        if self.action == 'list':
            # 1. Capturamos los parámetros posibles de la URL
            estado = self.request.query_params.get('estado', None)
            activo_param = self.request.query_params.get('activo', None)

            # 2. Si el frontend usa los filtros nuevos de Claude (?activo=true/false)
            # Retornamos el queryset limpio para que DjangoFilterBackend aplique el filtro
            if activo_param is not None:
                return queryset

            # 3. Lógica original: Si usa tu sistema anterior (?estado=inactivo/todos)
            if estado == 'inactivo':
                return queryset.filter(activo=False)
            elif estado == 'todos':
                return queryset  # Devuelve la tabla completa sin filtros
            else:
                # Comportamiento por defecto estricto: Mostrar solo los activos
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
from rest_framework.pagination import PageNumberPagination


class PaginacionRetrocompatible(PageNumberPagination):
    page_size = 5  # Por defecto traerá 5 registros por página
    page_size_query_param = (
        "page_size"  # Permite al frontend pedir más (ej. ?page=1&page_size=50)
    )
    max_page_size = 100  # Límite de seguridad para que no saturen tu BD

    def paginate_queryset(self, queryset, request, view=None):
        """
        Si el frontend NO manda el parámetro '?page=' en la URL,
        apagamos la paginación y devolvemos la lista plana para no romper nada.
        """
        if not request.query_params.get(self.page_query_param):
            return None

            # Si mandan '?page=', usamos el comportamiento normal de paginación de Django
        return super().paginate_queryset(queryset, request, view)

from django.db.models import QuerySet
from .models import Asistencia

def obtener_asistencias_optimizadas() -> QuerySet:
    """
    Selector base para la grilla de asistencias.
    Trae los datos del usuario acoplados para evitar consultas N+1.
    """
    return Asistencia.objects.select_related(
        'id_usuario',
        'id_sucursal'
    ).filter(activo=True).order_by('fecha', 'id_usuario__nombre_completo')
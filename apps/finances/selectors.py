from django.db.models import QuerySet
from .models import Asistencia

def obtener_asistencias_optimizadas() -> QuerySet:
    """
    Selector base para la grilla de asistencias.
    Trae los datos del usuario acoplados y excluye al nivel Gerencial (Dueño).
    """
    return Asistencia.objects.select_related(
        'id_usuario',
        'id_sucursal'
    ).filter(
        activo=True
    ).exclude(
        id_usuario__id_rol__codigo='DUENO'
    ).order_by('fecha', 'id_usuario__nombre_completo')
from django.utils import timezone
from django.db.models import QuerySet
from .models import Venta


def obtener_grabadores_disponibles(queryset_base: QuerySet) -> QuerySet:
    """
    Filtra el queryset de GrabadorAudio para devolver solo los disponibles hoy.
    Reglas de Negocio:
    1. Ocupado = Tiene venta creada HOY y la venta está ACTIVA.
    2. Excepción: El ID 1 (OTROS) siempre está disponible.
    """
    hoy = timezone.now().date()

    ids_bloqueados = Venta.objects.filter(
        fecha_creacion__date=hoy,
        activo=True
    ).exclude(
        id_grabador_audios=1  # REGLA DE ORO
    ).values_list('id_grabador_audios', flat=True)

    if ids_bloqueados:
        return queryset_base.exclude(id__in=ids_bloqueados)

    return queryset_base
from django.db.models import Exists, OuterRef, Prefetch, QuerySet
from apps.sales.models import Venta
from .models import Seguimiento

def obtener_seguimientos_optimizados(usuario_peticion) -> QuerySet:
    # 1. Recreamos la anotación vital de reingresos
    reingresos_activos = Venta.objects.filter(
        venta_origen=OuterRef('pk'), activo=True
    )

    # 2. Armamos la Venta OPTIMIZADA (El escudo anti-audios)
    ventas_optimizadas_qs = Venta.objects.select_related(
        'id_asesor', 'id_producto', 'id_estado_sot', 'id_sub_estado_sot',
        'id_estado_audios', 'id_tipo_documento', 'venta_origen'
    ).prefetch_related(
        'id_origen_venta__id_sucursal',
        'id_origen_venta__id_modalidad',
        'id_supervisor_vigente__id_supervisor',
        'id_distrito_nacimiento__id_provincia__id_departamento',
        'id_distrito_instalacion__id_provincia__id_departamento',
        'id_grabador_audios',
        'usuario_revision_audios'
        # ---> ¡MAGIA! Hemos quitado 'audios' de aquí. La BD ni se enterará de que existen. <---
    ).annotate(
        _ya_reingresada=Exists(reingresos_activos)
    )

    # 3. Ensamblamos el Seguimiento
    return Seguimiento.objects.prefetch_related(
        'meses_evaluados',
        Prefetch('id_venta', queryset=ventas_optimizadas_qs)
    ).filter(activo=True)
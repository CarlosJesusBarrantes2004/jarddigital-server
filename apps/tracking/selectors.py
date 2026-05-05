from django.db.models import Exists, OuterRef, Prefetch, QuerySet
from apps.sales.models import Venta
from .models import Seguimiento

from apps.sales.selectors import aplicar_rls_ventas


def obtener_seguimientos_optimizados(usuario_peticion) -> QuerySet:
    # 1. Creamos la base segura de Ventas
    ventas_seguras = aplicar_rls_ventas(Venta.objects.filter(activo=True), usuario_peticion)

    # 2. Recreamos la anotación de reingresos
    reingresos_activos = Venta.objects.filter(venta_origen=OuterRef('pk'), activo=True)

    # 3. Armamos la Venta OPTIMIZADA (SIN AUDIOS)
    ventas_optimizadas_qs = ventas_seguras.select_related(
        'id_asesor', 'id_producto', 'id_estado_sot', 'id_sub_estado_sot',
        'id_estado_audios', 'id_tipo_documento', 'venta_origen'
    ).prefetch_related(
        'id_origen_venta__id_sucursal', 'id_origen_venta__id_modalidad',
        'id_supervisor_vigente__id_supervisor',
        'id_distrito_nacimiento__id_provincia__id_departamento',
        'id_distrito_instalacion__id_provincia__id_departamento',
        'id_grabador_audios', 'usuario_revision_audios'
        # ---> Sin 'audios' <---
    ).annotate(
        _ya_reingresada=Exists(reingresos_activos)
    )

    # 4. Ensamblamos el Seguimiento (¡Si la Venta fue bloqueada por el RLS, el Seguimiento desaparece!)
    return Seguimiento.objects.prefetch_related(
        'meses_evaluados',
        Prefetch('id_venta', queryset=ventas_optimizadas_qs)
    ).filter(
        activo=True,
        # FILTRO VITAL: Solo trae el seguimiento si la venta anidada existe en el RLS
        id_venta__in=ventas_optimizadas_qs.values('id')
    )
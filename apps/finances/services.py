from django.db import transaction
from .models import Asistencia


@transaction.atomic
def upsert_asistencia_masiva(datos_validados: list[dict], id_sucursal: int, usuario_peticion) -> int:
    """
    Procesamiento masivo en memoria.
    1 Query de lectura + 1 Query de Inserción Masiva + 1 Query de Actualización Masiva.
    """
    if not datos_validados:
        return 0

    # 1. Extraemos las tuplas de búsqueda para aislar los registros afectados
    ids_usuarios = [item['id_usuario'].id for item in datos_validados]
    fechas = [item['fecha'] for item in datos_validados]

    # 2. Traemos todos los registros existentes (incluso los inactivos) de un solo golpe
    registros_existentes = Asistencia.objects.filter(
        id_usuario_id__in=ids_usuarios,
        fecha__in=fechas
    )

    # Mapeamos en RAM: {(id_usuario, fecha): objeto_asistencia}
    mapa_existentes = {(obj.id_usuario_id, obj.fecha): obj for obj in registros_existentes}

    a_crear = []
    a_actualizar = []

    # 3. Clasificación en memoria
    for item in datos_validados:
        uid = item['id_usuario'].id
        fecha = item['fecha']
        nuevo_estado = item.get('asistio')

        clave = (uid, fecha)

        if clave in mapa_existentes:
            obj = mapa_existentes[clave]
            obj.asistio = nuevo_estado
            obj.activo = True  # Punto 3 resuelto: Reactivación forzada
            a_actualizar.append(obj)
        else:
            a_crear.append(Asistencia(
                id_usuario_id=uid,
                id_sucursal_id=id_sucursal,
                fecha=fecha,
                asistio=nuevo_estado,
                activo=True
            ))

    # 4. Ejecución SQL Óptima
    if a_crear:
        Asistencia.objects.bulk_create(a_crear)
    if a_actualizar:
        Asistencia.objects.bulk_update(a_actualizar, fields=['asistio', 'activo'])

    return len(datos_validados)
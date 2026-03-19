from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from apps.sales.models import Venta
from apps.sales.serializers import VentaSerializer
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from .filters import VentaFilter

#Importamos utils necesarios para reporte de excel
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Side, Border
from openpyxl.utils import get_column_letter
from django.http import HttpResponse
from rest_framework.decorators import action

# Importamos tu papelera de reciclaje y tus aduanas
from apps.core.mixins import SoftDeleteModelViewSet
from apps.users.permissions import SoloLecturaOCrearSiEsJefe
from apps.users.models import PermisoAcceso

from .models import EstadoSOT, SubEstadoSOT, EstadoAudio, Producto, GrabadorAudio
from .serializers import (
    EstadoSOTSerializer,
    SubEstadoSOTSerializer,
    EstadoAudioSerializer,
    ProductoSerializer,
    GrabadorAudioSerializer
)


# ==========================================
# 1. CATÁLOGOS Y ESTADOS (Fase 1)
# ==========================================

class EstadoSOTViewSet(SoftDeleteModelViewSet):
    # Usamos order_by('orden') para que el frontend los pinte en el orden lógico del negocio
    queryset = EstadoSOT.objects.all().order_by('orden')
    serializer_class = EstadoSOTSerializer
    permission_classes = [IsAuthenticated, SoloLecturaOCrearSiEsJefe]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['nombre', 'codigo']


class SubEstadoSOTViewSet(SoftDeleteModelViewSet):
    queryset = SubEstadoSOT.objects.all()
    serializer_class = SubEstadoSOTSerializer
    permission_classes = [IsAuthenticated, SoloLecturaOCrearSiEsJefe]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['nombre']


class EstadoAudioViewSet(SoftDeleteModelViewSet):
    queryset = EstadoAudio.objects.all()
    serializer_class = EstadoAudioSerializer
    permission_classes = [IsAuthenticated, SoloLecturaOCrearSiEsJefe]
    filter_backends = [filters.SearchFilter]
    search_fields = ['nombre', 'codigo']


# ==========================================
# 2. OPERATIVOS Y PRODUCTOS (Fase 2)
# ==========================================

class ProductoViewSet(SoftDeleteModelViewSet):
    # Ordenamos por los más recientes primero
    queryset = Producto.objects.all().order_by('-fecha_inicio_vigencia')
    serializer_class = ProductoSerializer
    permission_classes = [IsAuthenticated, SoloLecturaOCrearSiEsJefe]

    # Activamos los filtros para que el asesor pueda buscar rápido su plan
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['es_alto_valor', 'nombre_campana', 'tipo_solucion', 'activo']  # ?es_alto_valor=True
    search_fields = ['nombre_paquete', 'nombre_campana']  # ?search=Max 29.90


class GrabadorAudioViewSet(viewsets.ReadOnlyModelViewSet):
    # El queryset base (trae todos)
    queryset = GrabadorAudio.objects.select_related('id_usuario').all().order_by('id')
    serializer_class = GrabadorAudioSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['nombre_completo']

    def get_queryset(self):
        # 1. Obtenemos la lista completa inicial
        queryset = super().get_queryset()

        # 2. Solo aplicamos la lógica de exclusión si estamos LISTANDO (para el dropdown)
        if self.action == 'list':
            hoy = timezone.now().date()

            # 3. Buscamos los grabadores que están "Ocupados" hoy.
            # REGLA: Ocupado = Tiene venta creada HOY y la venta está ACTIVA.
            # (Esto bloquea Rechazados, Pendientes, etc. Solo libera si activo=False es decir ANULADA)
            ids_bloqueados = Venta.objects.filter(
                fecha_creacion__date=hoy,
                activo=True
            ).exclude(
                # REGLA DE ORO: El ID 1 (OTROS) NUNCA entra en la lista negra.
                # Aunque tenga 1000 ventas activas hoy, lo sacamos de la lista de bloqueados.
                id_grabador_audios=1
            ).values_list('id_grabador_audios', flat=True)

            # 4. Excluimos los IDs bloqueados de la respuesta final
            if ids_bloqueados:
                queryset = queryset.exclude(id__in=ids_bloqueados)

        return queryset


# ==========================================
# 3. LA BESTIA: VENTAS (CORE)
# ==========================================

class VentaViewSet(SoftDeleteModelViewSet):
    serializer_class = VentaSerializer
    permission_classes = [IsAuthenticated]  # Todos deben estar logueados

    # Activamos los motores de búsqueda, filtros y ordenamiento
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    # 1. Filtros exactos para los combos del Backoffice
    filterset_class = VentaFilter

    # 2. Buscador libre (Para cuando el cliente llama reclamando y solo dan su DNI)
    search_fields = ["cliente_numero_doc", "cliente_nombre", "codigo_sec", "codigo_sot", "id_asesor__nombre_completo"]

    # 3. Ordenamiento (Por defecto, las ventas más nuevas arriba)
    ordering_fields = ['fecha_venta', 'fecha_creacion']
    ordering = ['-fecha_venta']

    #REPORTE DE EXCEL
    @action(detail=False, methods=['get'])
    def exportar_excel(self, request):
        # 1. RECIBIR FECHAS DEL FRONTEND (Si no mandan, exportamos todo por defecto)
        fecha_inicio = request.query_params.get('fecha_inicio')
        fecha_fin = request.query_params.get('fecha_fin')

        # 2. LA SÚPER CONSULTA (Optimizada para no colapsar la base de datos)
        ventas = Venta.objects.all().select_related(
            'id_producto',
            'id_estado_sot',
            'id_estado_audios',
            'id_asesor',
            'id_supervisor_vigente__id_supervisor',  # Asumiendo que va al usuario supervisor
            'id_supervisor_vigente__id_modalidad_sede__id_modalidad',
            'id_distrito_instalacion__id_provincia__id_departamento'
        )

        if fecha_inicio and fecha_fin:
            ventas = ventas.filter(fecha_venta__range=[fecha_inicio, fecha_fin])

        # 3. CREAR EL ARCHIVO EXCEL EN MEMORIA
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Reporte de Ventas"

        # 4. DEFINIR ESTILOS (Los colores y bordes del dueño)
        fill_cabecera = PatternFill(start_color='FFFF0000', end_color='FFFF0000', fill_type='solid')  # Rojo
        font_cabecera = Font(color='FFFFFFFF', italic=True, bold=True)  # Blanco cursiva

        fill_verde = PatternFill(start_color='FF86BF4E', end_color='FF86BF4E', fill_type='solid')  # Verde
        fill_mes_anio = PatternFill(start_color='FFE4CFC6', end_color='FFE4CFC6', fill_type='solid')  # Durazno

        # Definir borde delgado para todas las celdas
        borde_delgado = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )

        # Alineación centrada para todo el documento
        alineacion_centrada = Alignment(horizontal='center', vertical='center')

        # 5. ESCRIBIR LAS CABECERAS
        cabeceras = [
            "ITEM", "DNI/RUC", "CLIENTE", "SEC", "SOT", "TIPO", "TECN.", "PLAN", "C.FIJO",
            "SCORE", "COMEN", "EST.SOT", "FECHAINST.", "EST.AUDIO", "AUDIO", "SUBIDA",
            "SUPERV", "ASESOR", "FECHAVENTA", "MES", "MES INST.", "CELULAR", "C.PAGO",
            "AÑO", "AÑO INST.", "DEPARTAMENTO", "GÉNERO", "MODALIDAD"
        ]
        ws.append(cabeceras)

        # Aplicar estilo rojo a la fila 1 y ajustar altura
        for cell in ws[1]:
            cell.fill = fill_cabecera
            cell.font = font_cabecera
            cell.alignment = alineacion_centrada
            cell.border = borde_delgado

        # 6. LLENAR LOS DATOS FILA POR FILA
        for idx, venta in enumerate(ventas, start=1):

            # --- Lógica DNI/RUC ---
            # Directo al grano: si hay documento lo ponemos, si no, lo dejamos vacío.
            documento = venta.cliente_numero_doc if hasattr(venta, 'cliente_numero_doc') and venta.cliente_numero_doc else ""

            # --- Lógica Departamento ---
            departamento = ""
            if venta.id_distrito_instalacion and venta.id_distrito_instalacion.id_provincia:
                departamento = venta.id_distrito_instalacion.id_provincia.id_departamento.nombre

            # --- Lógica Fechas (Mes/Año) ---
            f_venta = venta.fecha_venta
            mes_vta = f_venta.month if f_venta else ""
            anio_vta = f_venta.year if f_venta else ""

            f_inst = venta.fecha_real_inst
            mes_inst = f_inst.month if f_inst else ""
            anio_inst = f_inst.year if f_inst else ""

            # --- Lógica Supervisor ---
            supervisor = ""
            modalidad = ""
            if venta.id_supervisor_vigente:
                if venta.id_supervisor_vigente.id_supervisor:
                    supervisor = venta.id_supervisor_vigente.id_supervisor.nombre_completo
                if venta.id_supervisor_vigente.id_modalidad_sede and venta.id_supervisor_vigente.id_modalidad_sede.id_modalidad:
                    modalidad = venta.id_supervisor_vigente.id_modalidad_sede.id_modalidad.nombre

            # --- Lógica Género (M/F) ---
            genero_inicial = ""
            if venta.cliente_genero:
                genero_mayuscula = venta.cliente_genero.upper()
                if genero_mayuscula == 'MASCULINO':
                    genero_inicial = 'M'
                elif genero_mayuscula == 'FEMENINO':
                    genero_inicial = 'F'
                else:
                    genero_inicial = venta.cliente_genero  # Por si envían 'NO ESPECIFICADO'

            # Armar la fila con el orden exacto de las cabeceras
            fila = [
                idx,  # ITEM
                documento,  # DNI/RUC
                venta.cliente_nombre,  # CLIENTE
                venta.codigo_sec or "",  # SEC
                venta.codigo_sot or "",  # SOT
                venta.tipo_venta or "",  # TIPO
                venta.tecnologia or "",  # TECN.
                venta.id_producto.nombre_paquete if venta.id_producto else "",  # PLAN
                venta.id_producto.costo_fijo_plan if venta.id_producto else "",  # C.FIJO
                venta.score_crediticio or "",  # SCORE
                venta.comentario_gestion or "",  # COMEN
                venta.id_estado_sot.nombre if venta.id_estado_sot else "",  # EST.SOT
                f_inst.strftime('%d/%m/%Y') if f_inst else "",  # FECHAINST.
                venta.id_estado_audios.nombre if venta.id_estado_audios else "",  # EST.AUDIO
                "✔" if venta.audio_subido else "",  # AUDIO
                venta.fecha_subida_audios.strftime('%d/%m/%Y') if venta.fecha_subida_audios else "",  # SUBIDA
                supervisor,  # SUPERV
                venta.id_asesor.nombre_completo if venta.id_asesor else "",  # ASESOR
                f_venta.strftime('%d/%m/%Y') if f_venta else "",  # FECHAVENTA
                mes_vta,  # MES
                mes_inst,  # MES INST.
                venta.cliente_telefono if hasattr(venta, 'cliente_telefono') else "",  # CELULAR
                "",  # C.PAGO (Vacío)
                anio_vta,  # AÑO
                anio_inst,  # AÑO INST.
                departamento,  # DEPARTAMENTO
                genero_inicial,  # GÉNERO
                modalidad  # MODALIDAD
            ]
            ws.append(fila)

            # --- Aplicar Colores, Bordes y Alineación a las Celdas ---
            fila_actual = ws[ws.max_row]

            # Iteramos sobre todas las celdas de la fila que acabamos de agregar
            for i, celda in enumerate(fila_actual):
                celda.alignment = alineacion_centrada
                celda.border = borde_delgado

                # Colorear EST.SOT (Col 12, index 11)
                if i == 11 and fila[11] and fila[11].upper() == 'ATENDIDO':
                    celda.fill = fill_verde
                # Colorear EST.AUDIO (Col 14, index 13)
                elif i == 13 and fila[13] and fila[13].upper() == 'CONFORME':
                    celda.fill = fill_verde
                # Colorear Meses (20, 21, index 19, 20) y Años (24, 25, index 23, 24)
                elif i in [19, 20, 23, 24]:
                    celda.fill = fill_mes_anio

        # 7. ACTIVAR EL AUTOFILTRO (Para todas las columnas)
        max_col_letra = get_column_letter(len(cabeceras))
        ws.auto_filter.ref = f"A1:{max_col_letra}{ws.max_row}"

        # =======================================================
        # AUTOAJUSTE INTELIGENTE DE COLUMNAS (El "Doble Clic")
        # =======================================================
        for col in ws.columns:
            max_length = 0
            col_letter = col[0].column_letter  # Obtenemos la letra (A, B, C...)

            # Recorremos todas las celdas de esa columna para buscar al más "gordo"
            for cell in col:
                try:
                    if cell.value:
                        # Convertimos el valor a texto y medimos su longitud
                        longitud_celda = len(str(cell.value))
                        if longitud_celda > max_length:
                            max_length = longitud_celda
                except:
                    pass

            # Le sumamos 2 espacios extra de "padding" para que respire y no quede pegado a la línea
            ancho_ajustado = (max_length + 5)

            # Si la columna es muy angosta (ej. el género "M"), le damos un mínimo para que se lea la cabecera
            if ancho_ajustado < 10:
                ancho_ajustado = 10

            ws.column_dimensions[col_letter].width = ancho_ajustado

        # 8. PREPARAR LA RESPUESTA HTTP (Despachar el archivo)
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="Reporte_Ventas.xlsx"'

        # Guardar el libro virtual en la respuesta HTTP
        wb.save(response)

        return response

    def get_queryset(self):
        user = self.request.user

        # ==========================================
        # FASE 1: OPTIMIZACIÓN EXTREMA (SQL JOINs)
        # ==========================================
        # Hacemos un JOIN masivo para que Django no haga consultas extra por cada llave foránea
        queryset = Venta.objects.select_related(
            'id_asesor',
            'id_origen_venta__id_sucursal',
            'id_origen_venta__id_modalidad',
            'id_supervisor_vigente__id_supervisor',
            'id_producto',
            'id_tipo_documento',
            'id_distrito_nacimiento',
            'id_distrito_instalacion',
            'id_sub_estado_sot',
            'id_estado_sot',
            'id_grabador_audios',
            'id_estado_audios',
            'usuario_revision_audios',
            'venta_origen'
        ).all()

        # ==========================================
        # FASE 2: SEGURIDAD DE DATOS (Tenant Isolation)
        # ==========================================
        # Verificamos qué tipo de usuario está pidiendo los datos
        if hasattr(user, 'id_rol') and user.id_rol:

            # Convertimos a mayúsculas por seguridad (ej. evita fallos si alguien escribe "Asesor")
            codigo_rol = user.id_rol.codigo.upper()

            # Candado ASESOR: Solo ve sus propias ventas
            if codigo_rol == 'ASESOR':
                queryset = queryset.filter(id_asesor=user)

            # Candado SUPERVISOR: Solo ve las ventas de sus sedes asignadas
            elif codigo_rol == 'SUPERVISOR':
                sedes_supervisadas = user.asignaciones_supervisor.filter(
                    activo=True,
                    fecha_fin__isnull=True
                ).values_list('id_modalidad_sede', flat=True)

                queryset = queryset.filter(id_origen_venta__in=sedes_supervisadas)

            # Candado BACKOFFICE: Solo ve las ventas de las sedes donde tiene permiso de acceso
            elif codigo_rol == 'BACKOFFICE':
                sedes_asignadas = PermisoAcceso.objects.filter(
                    id_usuario=user,
                    id_modalidad_sede__activo=True
                ).values_list('id_modalidad_sede', flat=True)

                queryset = queryset.filter(id_origen_venta__in=sedes_asignadas)

            # Si el rol es DUEÑO, los IFs lo ignoran y se le devuelve el queryset completo.

        return queryset
from django.db import models
from django.conf import settings
from apps.core.models import ModalidadSede, TipoDocumento
from apps.users.models import SupervisorAsignacion
from apps.ubigeo.models import Distrito

# ==========================================
# 1. CATÁLOGOS Y ESTADOS
# ==========================================

class EstadoSOT(models.Model):
    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)
    orden = models.IntegerField(null=True, blank=True)  # ¡Faltaba en tu código!
    es_final = models.BooleanField(default=False)
    color_hex = models.CharField(max_length=7)
    activo = models.BooleanField(default=True)  # Sugerencia de seguridad agregada

    class Meta:
        db_table = "estados_sot"


class SubEstadoSOT(models.Model):
    # ¡Tabla nueva del DBML!
    nombre = models.CharField(max_length=100)
    color_hex = models.CharField(max_length=7)
    requiere_nueva_fecha = models.BooleanField(default=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "sub_estados_sot"


class EstadoAudio(models.Model):
    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)
    activo = models.BooleanField(default=True)  # Sugerencia de seguridad agregada

    class Meta:
        db_table = "estados_audios"


# ==========================================
# 2. OPERATIVOS Y PRODUCTOS
# ==========================================

class GrabadorAudio(models.Model):
    id_usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        db_column="id_usuario"
    )  # ¡Faltaba esta relación!
    nombre_completo = models.CharField(max_length=200, unique=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "grabadores_audios"


class Producto(models.Model):
    nombre_plan = models.CharField(max_length=100)
    es_alto_valor = models.BooleanField(default=False)
    costo_fijo_plan = models.DecimalField(max_digits=10, decimal_places=2)
    comision_base = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_inicio_vigencia = models.DateField(auto_now_add=True)
    fecha_fin_vigencia = models.DateField(null=True, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "productos"


# ==========================================
# 3. LA BESTIA: VENTAS (CORE)
# ==========================================

class Venta(models.Model):
    # --- VINCULACIÓN ---
    id_asesor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="ventas_asesor", db_column="id_asesor"
    )
    id_origen_venta = models.ForeignKey(ModalidadSede, on_delete=models.PROTECT, db_column="id_origen_venta")
    id_supervisor_vigente = models.ForeignKey(SupervisorAsignacion, on_delete=models.PROTECT,
                                              db_column="id_supervisor_vigente")

    # --- PRODUCTO & CLIENTE ---
    id_producto = models.ForeignKey(Producto, on_delete=models.PROTECT, db_column="id_producto")
    tecnologia = models.CharField(max_length=20)
    id_tipo_documento = models.ForeignKey(TipoDocumento, on_delete=models.PROTECT, db_column="id_tipo_documento")
    cliente_numero_doc = models.CharField(max_length=20)
    cliente_nombre = models.CharField(max_length=200)
    cliente_telefono = models.CharField(max_length=20)
    cliente_email = models.EmailField(null=True, blank=True)
    id_distrito_nacimiento = models.ForeignKey(Distrito, on_delete=models.PROTECT, related_name='ventas_nacimiento',
                                               db_column="id_distrito_nacimiento", null=True)

    # --- UBICACIÓN Y DETALLES ---
    id_distrito_instalacion = models.ForeignKey(Distrito, on_delete=models.PROTECT, related_name='ventas_instalacion',
                                                db_column="id_distrito_instalacion")
    direccion_detalle = models.CharField(max_length=255)
    coordenadas_gps = models.CharField(max_length=100, null=True, blank=True)
    es_full_claro = models.BooleanField(default=False)
    score_crediticio = models.CharField(max_length=50, null=True, blank=True)

    # --- OPERATIVO ---
    codigo_sec = models.CharField(max_length=50, null=True, blank=True)
    codigo_sot = models.CharField(max_length=50, null=True, blank=True)
    fecha_venta = models.DateTimeField()

    # --- GESTIÓN DE CITAS (FILTROS) ---
    fecha_visita_programada = models.DateField(null=True, blank=True)
    bloque_horario = models.CharField(max_length=50, null=True, blank=True)
    id_sub_estado_sot = models.ForeignKey(SubEstadoSOT, on_delete=models.SET_NULL, null=True,
                                          db_column="id_sub_estado_sot")

    # --- ESTADOS FINALES ---
    fecha_real_inst = models.DateTimeField(null=True, blank=True)
    fecha_rechazo = models.DateTimeField(null=True, blank=True)
    id_estado_sot = models.ForeignKey(EstadoSOT, on_delete=models.PROTECT, db_column="id_estado_sot")
    comentario_gestion = models.TextField(null=True, blank=True)

    # --- AUDIOS ---
    id_grabador_audios = models.ForeignKey(GrabadorAudio, on_delete=models.SET_NULL, null=True,
                                           db_column="id_grabador_audios")
    audio_subido = models.BooleanField(default=False)
    fecha_subida_audios = models.DateTimeField(null=True, blank=True)

    id_estado_audios = models.ForeignKey(EstadoAudio, on_delete=models.SET_NULL, null=True,
                                         db_column="id_estado_audios")
    fecha_revision_audios = models.DateTimeField(null=True, blank=True)
    usuario_revision_audios = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                                related_name="audios_revisados", db_column="usuario_revision_audios")
    observacion_audios = models.TextField(null=True, blank=True)

    # --- AUDITORÍA Y BORRADO LÓGICO ---
    usuario_creacion = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                         related_name="ventas_creadas", db_column="usuario_creacion")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    usuario_modificacion = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                             related_name="ventas_modificadas", db_column="usuario_modificacion")
    fecha_modificacion = models.DateTimeField(auto_now=True)
    activo = models.BooleanField(default=True)  # ¡Salvavidas añadido!

    class Meta:
        db_table = "ventas"
        indexes = [
            models.Index(fields=['fecha_visita_programada', 'id_sub_estado_sot'], name='idx_filtro_agenda'),
        ]


# ==========================================
# 4. RASTREO Y ARCHIVOS
# ==========================================

class HistorialAgendaSOT(models.Model):
    # ¡Tabla nueva del DBML!
    id_venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name="historial_agenda", db_column="id_venta")
    fecha_anterior = models.DateField(null=True, blank=True)
    fecha_nueva = models.DateField()
    id_sub_estado_motivo = models.ForeignKey(SubEstadoSOT, on_delete=models.PROTECT, db_column="id_sub_estado_motivo")
    usuario_responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                            db_column="usuario_responsable")
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "historial_agenda_sot"


class AudioVenta(models.Model):
    id_venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name="audios", db_column="id_venta")
    nombre_etiqueta = models.CharField(max_length=100)
    url_audio = models.CharField(max_length=255)
    fecha_subida = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)  # ¡Añadido para el borrado lógico!

    class Meta:
        db_table = "audios_venta"
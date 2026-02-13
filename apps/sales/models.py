from django.db import models
from django.conf import settings
from apps.core.models import ModalidadSede, SupervisorAsignacion

# --- CATÁLOGOS ---

class TipoDocumento(models.Model):
    codigo = models.CharField(max_length=10, unique=True)
    nombre = models.CharField(max_length=100)
    longitud_exacta = models.IntegerField()
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'tipos_documento'


class EstadoSOT(models.Model):
    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)
    es_final = models.BooleanField(default=False)
    color_hex = models.CharField(max_length=7)

    class Meta:
        db_table = 'estados_sot'


class EstadoAudio(models.Model):
    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)

    class Meta:
        db_table = 'estados_audios'


class GrabadorAudio(models.Model):
    nombre_completo = models.CharField(max_length=200, unique=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'grabadores_audios'


# --- PRODUCTOS ---

class Producto(models.Model):
    nombre_plan = models.CharField(max_length=100)
    es_alto_valor = models.BooleanField(default=False)
    costo_fijo_plan = models.DecimalField(max_digits=10, decimal_places=2)
    comision_base = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_inicio_vigencia = models.DateField(auto_now_add=True)
    fecha_fin_vigencia = models.DateField(null=True, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'productos'


# --- VENTAS (CORE) ---

class Venta(models.Model):
    # Relaciones de Estructura
    id_asesor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='ventas_asesor')
    id_origen_venta = models.ForeignKey(ModalidadSede, on_delete=models.PROTECT)
    id_supervisor_vigente = models.ForeignKey(SupervisorAsignacion, on_delete=models.PROTECT)

    # Producto
    id_producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    tecnologia = models.CharField(max_length=20)  # FTTH, HFC

    # Datos del Cliente
    id_tipo_documento = models.ForeignKey(TipoDocumento, on_delete=models.PROTECT)
    cliente_numero_doc = models.CharField(max_length=20)
    cliente_nombre = models.CharField(max_length=200)
    cliente_genero = models.CharField(max_length=20, null=True)
    cliente_fecha_nacimiento = models.DateField(null=True)
    cliente_telefono = models.CharField(max_length=20)
    cliente_telefono_2 = models.CharField(max_length=20, null=True, blank=True)
    cliente_email = models.EmailField(null=True, blank=True)

    # Ubicación y Operativos
    direccion_detalle = models.CharField(max_length=255)
    direccion_referencia = models.CharField(max_length=255, null=True, blank=True)
    coordenadas_gps = models.CharField(max_length=100, null=True, blank=True)
    codigo_sec = models.CharField(max_length=50, null=True, blank=True)
    codigo_sot = models.CharField(max_length=50, null=True, blank=True)

    # Estados y Fechas
    fecha_venta = models.DateTimeField(auto_now_add=True)
    fecha_real_inst = models.DateTimeField(null=True, blank=True)
    id_estado_sot = models.ForeignKey(EstadoSOT, on_delete=models.PROTECT)
    comentario_gestion = models.TextField(null=True, blank=True)

    # Audios
    id_grabador_audios = models.ForeignKey(GrabadorAudio, on_delete=models.SET_NULL, null=True)
    audio_subido = models.BooleanField(default=False)
    id_estado_audios = models.ForeignKey(EstadoAudio, on_delete=models.SET_NULL, null=True)

    # Auditoría
    usuario_creacion = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                         related_name='ventas_creadas')
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ventas'


class AudioVenta(models.Model):
    id_venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='audios')
    nombre_etiqueta = models.CharField(max_length=100)
    url_audio = models.CharField(max_length=255)
    fecha_subida = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'audios_venta'
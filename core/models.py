from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


# ==========================================
# 1. ORGANIZACIÓN Y JERARQUÍA
# ==========================================

class Sucursal(models.Model):
    nombre = models.CharField(max_length=100)
    direccion = models.CharField(max_length=255, blank=True, null=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre


class Modalidad(models.Model):
    # Tabla Maestra (Catálogo)
    nombre = models.CharField(max_length=50, help_text='CALL, CAMPO')
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre


class ModalidadSede(models.Model):
    # Configuración de la Sede (Unión)
    sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE)
    modalidad = models.ForeignKey(Modalidad, on_delete=models.CASCADE)
    nombre_supervisor = models.CharField(max_length=200, help_text='Ej: Juan Perez (Supervisor de JLO-Call)')
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.sucursal.nombre} - {self.modalidad.nombre} ({self.nombre_supervisor})"


# === USUARIO PERSONALIZADO (LOGIN) ===
class Usuario(AbstractUser):
    # Django ya trae 'username' (tu campo 'usuario') y 'password' (tu 'contrasena')
    # También trae 'first_name' y 'last_name', pero usaremos tu campo 'nombre_completo'

    ROLES_CHOICES = [
        ('DUENO', 'Dueño'),
        ('ASESOR', 'Asesor'),
        ('BACKOFFICE', 'BackOffice'),
        ('RRHH', 'RRHH'),
    ]

    nombre_completo = models.CharField(max_length=200)
    rol_sistema = models.CharField(max_length=20, choices=ROLES_CHOICES)
    activo = models.BooleanField(default=True)

    # Configuración requerida por Django para usuarios personalizados
    def __str__(self):
        return f"{self.username} - {self.rol_sistema}"


class PermisoAcceso(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='permisos')
    modalidad_sede = models.ForeignKey(ModalidadSede, on_delete=models.CASCADE)


# ==========================================
# 2. PRODUCTOS Y COMISIONES
# ==========================================

class Producto(models.Model):
    nombre_plan = models.CharField(max_length=150)
    es_alto_valor = models.BooleanField(default=False)
    comision_base = models.DecimalField(max_digits=10, decimal_places=2)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre_plan


class ReglaSalarialMensual(models.Model):
    anio = models.IntegerField()
    mes = models.IntegerField()
    dias_laborables_mes = models.IntegerField(default=30)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.mes}/{self.anio}"


class EscalaSueldo(models.Model):
    regla_salarial = models.ForeignKey(ReglaSalarialMensual, on_delete=models.CASCADE)
    nombre_escala = models.CharField(max_length=100)
    minimo_ventas_requeridas = models.IntegerField()
    sueldo_base_nivel = models.DecimalField(max_digits=10, decimal_places=2)
    meta_alto_valor_requerida = models.IntegerField()
    porcentaje_comision_full = models.DecimalField(max_digits=5, decimal_places=2)
    porcentaje_comision_penalizada = models.DecimalField(max_digits=5, decimal_places=2)


# ==========================================
# 3. VENTAS (CORE)
# ==========================================

class Venta(models.Model):
    ESTADOS_SOT = [('Pendiente', 'Pendiente'), ('Ejecucion', 'Ejecución'), ('Instalada', 'Instalada'),
                   ('Rechazada', 'Rechazada')]

    # Origen
    asesor = models.ForeignKey(Usuario, on_delete=models.PROTECT)
    origen_venta = models.ForeignKey(ModalidadSede, on_delete=models.PROTECT, related_name='ventas')

    # Producto
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    tecnologia = models.CharField(max_length=20)  # FTTH, HFC
    costo_fijo_plan = models.DecimalField(max_digits=10, decimal_places=2)

    # Cliente
    cliente_tipo_doc = models.CharField(max_length=20)
    cliente_numero_doc = models.CharField(max_length=20)
    cliente_nombre = models.CharField(max_length=200)
    cliente_genero = models.CharField(max_length=20, blank=True)
    cliente_fecha_nacimiento = models.DateField(null=True, blank=True)
    cliente_telefono = models.CharField(max_length=20)
    cliente_telefono_2 = models.CharField(max_length=20, blank=True)
    cliente_email = models.CharField(max_length=100, blank=True)

    # Datos Adicionales
    nacimiento_departamento = models.CharField(max_length=100, blank=True)
    nacimiento_provincia = models.CharField(max_length=100, blank=True)
    nacimiento_distrito = models.CharField(max_length=100, blank=True)
    nombre_padre = models.CharField(max_length=200, blank=True)
    nombre_madre = models.CharField(max_length=200, blank=True)

    # Ubicación
    direccion_departamento = models.CharField(max_length=100, blank=True)
    direccion_provincia = models.CharField(max_length=100, blank=True)
    direccion_distrito = models.CharField(max_length=100, blank=True)
    direccion_detalle = models.TextField(blank=True)
    direccion_referencia = models.TextField(blank=True)
    coordenadas_gps = models.CharField(max_length=100, blank=True)
    plano_ubicacion = models.CharField(max_length=255, blank=True)  # URL o Path
    es_full_claro = models.BooleanField(default=False)

    # Operativos
    score_crediticio = models.CharField(max_length=50, blank=True)
    codigo_sec = models.CharField(max_length=50, blank=True)
    codigo_sot = models.CharField(max_length=50, blank=True)
    codigo_pago = models.CharField(max_length=50, blank=True)

    # Fechas y Estados
    fecha_venta = models.DateTimeField(default=timezone.now)
    fecha_propuesta_inst = models.DateTimeField(null=True, blank=True)
    fecha_real_inst = models.DateTimeField(null=True, blank=True)
    fecha_rechazo = models.DateTimeField(null=True, blank=True)

    estado_sot = models.CharField(max_length=20, choices=ESTADOS_SOT, default='Pendiente')
    comentario_gestion = models.TextField(blank=True)

    # Control Audios
    audio_subido = models.BooleanField(default=False)
    estado_audios_general = models.CharField(max_length=50, blank=True)  # Conforme / No Conforme
    fecha_subida_audios_general = models.DateTimeField(null=True, blank=True)


class AudioVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='audios')
    url_audio = models.CharField(max_length=500)
    nombre_etiqueta = models.CharField(max_length=100)
    fecha_expiracion = models.DateTimeField(null=True, blank=True)
    backup_realizado = models.BooleanField(default=False)


# ==========================================
# 4. FINANZAS Y RRHH
# ==========================================

class Asistencia(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE)
    fecha = models.DateField()
    hora_entrada = models.TimeField(null=True)
    hora_salida = models.TimeField(null=True)
    estado = models.CharField(max_length=20)  # Asistió, Falta, Tardanza


class LiquidacionMensualAsesor(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT)
    anio = models.IntegerField()
    mes = models.IntegerField()

    total_ventas_instaladas = models.IntegerField()
    total_alto_valor_logradas = models.IntegerField()

    escala_alcanzada = models.ForeignKey(EscalaSueldo, on_delete=models.PROTECT)

    dias_falta = models.IntegerField()
    monto_descuento_inasistencias = models.DecimalField(max_digits=10, decimal_places=2)

    cumplio_meta_alto_valor = models.BooleanField()
    porcentaje_comision_aplicado = models.DecimalField(max_digits=5, decimal_places=2)
    monto_total_comisiones = models.DecimalField(max_digits=10, decimal_places=2)

    monto_final_pago = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_calculo = models.DateTimeField(auto_now=True)
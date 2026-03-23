from django.core.management.base import BaseCommand
from apps.users.models import RolSistema, Usuario
from apps.core.models import TipoDocumento, Modalidad, Sucursal
from apps.ubigeo.models import Departamento, Provincia, Distrito

# ¡Importamos los nuevos modelos de ventas!
from apps.sales.models import (
    EstadoAudio,
    EstadoSOT,
    SubEstadoSOT,
    Producto,
    GrabadorAudio,
)


class Command(BaseCommand):
    help = "Puebla la base de datos con los catálogos iniciales (Roles, Documentos, Sucursales, Modalidades y Catálogos de Ventas)"

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING("Iniciando población de base de datos..."))

        # ==========================================
        # MÓDULOS CORE Y USERS
        # ==========================================

        # 1. POBLAR ROLES
        roles = [
            {
                "codigo": "DUENO",
                "nombre": "Dueño",
                "descripcion": "Acceso total",
                "nivel_jerarquia": 1,
            },
            {
                "codigo": "SUPERVISOR",
                "nombre": "Supervisor",
                "descripcion": "Gestiona sede",
                "nivel_jerarquia": 2,
            },
            {
                "codigo": "RRHH",
                "nombre": "Recursos Humanos",
                "descripcion": "Asistencias",
                "nivel_jerarquia": 2,
            },
            {
                "codigo": "BACKOFFICE",
                "nombre": "BackOffice",
                "descripcion": "Liquidador",
                "nivel_jerarquia": 3,
            },
            {
                "codigo": "ASESOR",
                "nombre": "Asesor",
                "descripcion": "Ventas",
                "nivel_jerarquia": 4,
            },
        ]

        for r in roles:
            RolSistema.objects.get_or_create(codigo=r["codigo"], defaults=r)
        self.stdout.write(
            self.style.SUCCESS("✅ Roles del sistema verificados/creados.")
        )

        # 2. POBLAR TIPOS DE DOCUMENTO
        documentos = [
            {
                "codigo": "DNI",
                "nombre": "Documento Nacional de Identidad",
                "longitud_exacta": 8,
            },
            {"codigo": "CE", "nombre": "Carné de Extranjería", "longitud_exacta": 9},
            {
                "codigo": "RUC",
                "nombre": "Registro Único de Contribuyentes",
                "longitud_exacta": 11,
            },
        ]

        for d in documentos:
            TipoDocumento.objects.get_or_create(codigo=d["codigo"], defaults=d)
        self.stdout.write(
            self.style.SUCCESS("✅ Tipos de documento verificados/creados.")
        )

        # 3. POBLAR MODALIDADES
        modalidades = ["CALL CENTER", "CAMPO"]
        for nombre_mod in modalidades:
            Modalidad.objects.get_or_create(nombre=nombre_mod)
        self.stdout.write(
            self.style.SUCCESS("✅ Modalidades de trabajo verificadas/creadas.")
        )

        # 4. POBLAR SUCURSALES (Ejemplos iniciales)
        sucursales = [
            {
                "nombre": "Principal",
                "direccion": "Av. Balta 3633, José Leonardo Ortiz",
            },
            {"nombre": "Secundaria", "direccion": "Chiclato, Elías Aguirre"},
        ]

        for s in sucursales:
            Sucursal.objects.get_or_create(nombre=s["nombre"], defaults=s)
        self.stdout.write(
            self.style.SUCCESS("✅ Sucursales iniciales verificadas/creadas.")
        )

        # ==========================================
        # MÓDULO SALES (NUEVO)
        # ==========================================

        # 9. POBLAR GRABADORES (Lógica Híbrida)
        # 9.1 Creamos el registro por defecto "OTROS" (Sin usuario asociado)
        GrabadorAudio.objects.get_or_create(
            nombre_completo="OTROS", defaults={"id_usuario": None, "activo": True}
        )

        # 9.2 Sincronizamos usuarios existentes que NO sean Backoffice
        # Esto es útil si ya creaste usuarios antes de implementar el Signal
        usuarios_aptos = Usuario.objects.exclude(id_rol__codigo="BACKOFFICE")

        for u in usuarios_aptos:
            GrabadorAudio.objects.get_or_create(
                id_usuario=u,
                defaults={"nombre_completo": u.nombre_completo, "activo": u.activo},
            )

        self.stdout.write(
            self.style.SUCCESS(
                "✅ Grabadores (OTROS + Usuarios) verificados/sincronizados."
            )
        )

        # 5. POBLAR ESTADOS DE AUDIO
        estados_audio = [
            {"codigo": "CONFORME", "nombre": "Conforme"},
            {"codigo": "PENDIENTE", "nombre": "Pendiente"},
            {"codigo": "RECHAZADO", "nombre": "Rechazado"},
        ]
        for ea in estados_audio:
            EstadoAudio.objects.get_or_create(codigo=ea["codigo"], defaults=ea)
        self.stdout.write(
            self.style.SUCCESS("✅ Estados de Audio verificados/creados.")
        )

        # 6. POBLAR ESTADOS SOT
        estados_sot = [
            {
                "codigo": "ATENDIDO",
                "nombre": "Atendido",
                "orden": 1,
                "es_final": False,
                "color_hex": "#3498db",
            },  # Azul
            {
                "codigo": "EJECUCION",
                "nombre": "Ejecución",
                "orden": 2,
                "es_final": False,
                "color_hex": "#f1c40f",
            },  # Amarillo
            {
                "codigo": "RECHAZADO",
                "nombre": "Rechazado",
                "orden": 3,
                "es_final": True,
                "color_hex": "#e74c3c",
            },  # Rojo
        ]
        for es in estados_sot:
            EstadoSOT.objects.get_or_create(codigo=es["codigo"], defaults=es)
        self.stdout.write(self.style.SUCCESS("✅ Estados SOT verificados/creados."))

        # 7. POBLAR SUB ESTADOS SOT
        sub_estados_sot = [
            {
                "nombre": "Reagendado por cliente",
                "requiere_nueva_fecha": True,
                "color_hex": "#e67e22",
            },  # Naranja
            {
                "nombre": "Reagendado por claro",
                "requiere_nueva_fecha": True,
                "color_hex": "#9b59b6",
            },  # Morado
        ]
        for ses in sub_estados_sot:
            SubEstadoSOT.objects.get_or_create(nombre=ses["nombre"], defaults=ses)
        self.stdout.write(self.style.SUCCESS("✅ Sub Estados SOT verificados/creados."))

        # 8. POBLAR PRODUCTOS (Con precios base de prueba)
        productos = [
            {
                "nombre_campana": "REGULAR",
                "tipo_solucion": "2 PLAY",
                "nombre_paquete": "400 MBPS TV",
                "es_alto_valor": True,
                "costo_fijo_plan": 85.00,
                "comision_base": 55.00,
            },
            {
                "nombre_campana": "RELAMPAGO",
                "tipo_solucion": "2 PLAY",
                "nombre_paquete": "400 MBPS FIJO 5000",
                "es_alto_valor": False,
                "costo_fijo_plan": 47.00,
                "comision_base": 23.50,
            },
        ]
        for p in productos:
            # Usamos nombre_paquete como identificador único para el get_or_create
            Producto.objects.get_or_create(
                nombre_paquete=p["nombre_paquete"], defaults=p
            )
        self.stdout.write(self.style.SUCCESS("✅ Productos verificados/creados."))

        self.stdout.write(self.style.SUCCESS("🎉 ¡Base de datos poblada con éxito!"))

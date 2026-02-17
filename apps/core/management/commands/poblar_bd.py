from django.core.management.base import BaseCommand
from apps.users.models import RolSistema
from apps.core.models import TipoDocumento, Modalidad, Sucursal
# ¡Importamos los nuevos modelos de ventas!
from apps.sales.models import EstadoAudio, EstadoSOT, SubEstadoSOT, Producto

class Command(BaseCommand):
    help = 'Puebla la base de datos con los catálogos iniciales (Roles, Documentos, Sucursales, Modalidades y Catálogos de Ventas)'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('Iniciando población de base de datos...'))

        # ==========================================
        # MÓDULOS CORE Y USERS
        # ==========================================

        # 1. POBLAR ROLES
        roles = [
            {'codigo': 'DUENO', 'nombre': 'Dueño', 'descripcion': 'Acceso total', 'nivel_jerarquia': 1},
            {'codigo': 'SUPERVISOR', 'nombre': 'Supervisor', 'descripcion': 'Gestiona sede', 'nivel_jerarquia': 2},
            {'codigo': 'RRHH', 'nombre': 'Recursos Humanos', 'descripcion': 'Asistencias', 'nivel_jerarquia': 2},
            {'codigo': 'BACKOFFICE', 'nombre': 'BackOffice', 'descripcion': 'Liquidador', 'nivel_jerarquia': 3},
            {'codigo': 'ASESOR', 'nombre': 'Asesor', 'descripcion': 'Ventas', 'nivel_jerarquia': 4},
        ]

        for r in roles:
            RolSistema.objects.get_or_create(codigo=r['codigo'], defaults=r)
        self.stdout.write(self.style.SUCCESS('✅ Roles del sistema verificados/creados.'))

        # 2. POBLAR TIPOS DE DOCUMENTO
        documentos = [
            {'codigo': 'DNI', 'nombre': 'Documento Nacional de Identidad', 'longitud_exacta': 8},
            {'codigo': 'CE', 'nombre': 'Carné de Extranjería', 'longitud_exacta': 9},
            {'codigo': 'RUC', 'nombre': 'Registro Único de Contribuyentes', 'longitud_exacta': 11},
        ]

        for d in documentos:
            TipoDocumento.objects.get_or_create(codigo=d['codigo'], defaults=d)
        self.stdout.write(self.style.SUCCESS('✅ Tipos de documento verificados/creados.'))

        # 3. POBLAR MODALIDADES
        modalidades = ['CALL CENTER', 'CAMPO']
        for nombre_mod in modalidades:
            Modalidad.objects.get_or_create(nombre=nombre_mod)
        self.stdout.write(self.style.SUCCESS('✅ Modalidades de trabajo verificadas/creadas.'))

        # 4. POBLAR SUCURSALES (Ejemplos iniciales)
        sucursales = [
            {'nombre': 'JLO - Chiclayo', 'direccion': 'Av. Balta 3633, José Leonardo Ortiz'},
            {'nombre': 'Sede Piura', 'direccion': 'Centro de Piura, Zona Norte'}
        ]

        for s in sucursales:
            Sucursal.objects.get_or_create(nombre=s['nombre'], defaults=s)
        self.stdout.write(self.style.SUCCESS('✅ Sucursales iniciales verificadas/creadas.'))


        # ==========================================
        # MÓDULO SALES (NUEVO)
        # ==========================================

        # 5. POBLAR ESTADOS DE AUDIO
        estados_audio = [
            {'codigo': 'CONFORME', 'nombre': 'Conforme'},
            {'codigo': 'PENDIENTE', 'nombre': 'Pendiente'},
            {'codigo': 'RECHAZADO', 'nombre': 'Rechazado'},
        ]
        for ea in estados_audio:
            EstadoAudio.objects.get_or_create(codigo=ea['codigo'], defaults=ea)
        self.stdout.write(self.style.SUCCESS('✅ Estados de Audio verificados/creados.'))

        # 6. POBLAR ESTADOS SOT
        estados_sot = [
            {'codigo': 'ATENDIDO', 'nombre': 'Atendido', 'orden': 1, 'es_final': False, 'color_hex': '#3498db'}, # Azul
            {'codigo': 'EJECUCION', 'nombre': 'Ejecución', 'orden': 2, 'es_final': False, 'color_hex': '#f1c40f'}, # Amarillo
            {'codigo': 'RECHAZADO', 'nombre': 'Rechazado', 'orden': 3, 'es_final': True, 'color_hex': '#e74c3c'}, # Rojo
        ]
        for es in estados_sot:
            EstadoSOT.objects.get_or_create(codigo=es['codigo'], defaults=es)
        self.stdout.write(self.style.SUCCESS('✅ Estados SOT verificados/creados.'))

        # 7. POBLAR SUB ESTADOS SOT
        sub_estados_sot = [
            {'nombre': 'Reagendado por cliente', 'requiere_nueva_fecha': True, 'color_hex': '#e67e22'}, # Naranja
            {'nombre': 'Reagendado por claro', 'requiere_nueva_fecha': True, 'color_hex': '#9b59b6'}, # Morado
        ]
        for ses in sub_estados_sot:
            SubEstadoSOT.objects.get_or_create(nombre=ses['nombre'], defaults=ses)
        self.stdout.write(self.style.SUCCESS('✅ Sub Estados SOT verificados/creados.'))

        # 8. POBLAR PRODUCTOS (Con precios base de prueba)
        productos = [
            {'nombre_plan': '2 play fijo 400', 'es_alto_valor': False, 'costo_fijo_plan': 60.00, 'comision_base': 30.00},
            {'nombre_plan': '2 play tv 400', 'es_alto_valor': True, 'costo_fijo_plan': 120.00, 'comision_base': 60.00},
        ]
        for p in productos:
            Producto.objects.get_or_create(nombre_plan=p['nombre_plan'], defaults=p)
        self.stdout.write(self.style.SUCCESS('✅ Productos verificados/creados.'))


        self.stdout.write(self.style.SUCCESS('🎉 ¡Base de datos poblada con éxito!'))
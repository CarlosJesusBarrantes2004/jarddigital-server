from django.core.management.base import BaseCommand
from apps.users.models import RolSistema
from apps.core.models import TipoDocumento, Modalidad, Sucursal  # <-- Agregamos Modalidad y Sucursal

class Command(BaseCommand):
    help = 'Puebla la base de datos con los catálogos iniciales (Roles, Documentos, Sucursales, Modalidades)'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('Iniciando población de base de datos...'))

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
            # Aquí buscamos por nombre. Si no existe, lo crea con activo=True por defecto
            Modalidad.objects.get_or_create(nombre=nombre_mod)
        self.stdout.write(self.style.SUCCESS('✅ Modalidades de trabajo verificadas/creadas.'))

        # 4. POBLAR SUCURSALES (Ejemplos iniciales)
        sucursales = [
            {'nombre': 'JLO - Chiclayo', 'direccion': 'Av. Balta 3633, José Leonardo Ortiz'},
            {'nombre': 'Sede Piura', 'direccion': 'Centro de Piura, Zona Norte'}
        ]

        for s in sucursales:
            # Busca por el nombre de la sucursal, si no está, la crea con su dirección
            Sucursal.objects.get_or_create(nombre=s['nombre'], defaults=s)
        self.stdout.write(self.style.SUCCESS('✅ Sucursales iniciales verificadas/creadas.'))

        self.stdout.write(self.style.SUCCESS('🎉 ¡Base de datos poblada con éxito!'))
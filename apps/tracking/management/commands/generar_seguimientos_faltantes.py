"""
=========================================================================
SCRIPT DE MIGRACIÓN: Generar Seguimientos Faltantes
=========================================================================
Este comando busca TODAS las ventas en estado ATENDIDO que NO tienen
un registro de Seguimiento creado, y les genera:
  - 1 cabecera de Seguimiento (con ciclo de facturación calculado)
  - 6 registros de SeguimientoMensual (con fechas proyectadas)

USO:
  python manage.py generar_seguimientos_faltantes          (modo simulación)
  python manage.py generar_seguimientos_faltantes --aplicar (modo real)
=========================================================================
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.sales.models import Venta
from apps.tracking.models import Seguimiento, SeguimientoMensual
from apps.tracking.utils_seguimiento import generar_fechas_proyectadas


class Command(BaseCommand):
    help = "Genera seguimientos + 6 meses para ventas ATENDIDAS que no tienen seguimiento."

    def add_arguments(self, parser):
        parser.add_argument(
            '--aplicar',
            action='store_true',
            default=False,
            help='Si se omite, solo muestra lo que haría (modo simulación). Con --aplicar, ejecuta los cambios.',
        )

    def handle(self, *args, **options):
        aplicar = options['aplicar']

        # 1. Buscar ventas ATENDIDAS sin seguimiento
        ventas_sin_seguimiento = Venta.objects.filter(
            activo=True,
            id_estado_sot__codigo__iexact='ATENDIDO',
            fecha_real_inst__isnull=False,  # Necesitamos la fecha de instalación para calcular
        ).exclude(
            seguimiento__isnull=False  # Excluir las que YA tienen seguimiento
        ).select_related('id_estado_sot', 'id_asesor', 'id_producto')

        total = ventas_sin_seguimiento.count()

        if total == 0:
            self.stdout.write(self.style.SUCCESS(
                "\n✅ No hay ventas huérfanas. Todas las ventas ATENDIDAS ya tienen su seguimiento.\n"
            ))
            return

        self.stdout.write(self.style.WARNING(
            f"\n{'='*60}"
            f"\n  Se encontraron {total} ventas ATENDIDAS SIN seguimiento."
            f"\n{'='*60}\n"
        ))

        # 2. Mostrar resumen de lo que se va a crear
        for i, venta in enumerate(ventas_sin_seguimiento, start=1):
            fecha_inst = venta.fecha_real_inst
            # fecha_real_inst puede ser DateTimeField, extraemos solo la fecha
            if hasattr(fecha_inst, 'date'):
                fecha_inst = fecha_inst.date()

            paquete = generar_fechas_proyectadas(fecha_real_instalacion=fecha_inst)

            self.stdout.write(
                f"  {i:3d}. SOT: {venta.codigo_sot or 'N/A':<15} "
                f"| Cliente: {venta.cliente_nombre:<30} "
                f"| F.Inst: {fecha_inst} "
                f"| Ciclo: {paquete['ciclo_facturacion']}"
            )

        if not aplicar:
            self.stdout.write(self.style.WARNING(
                f"\n{'='*60}"
                f"\n  MODO SIMULACIÓN: No se creó nada en la base de datos."
                f"\n  Para ejecutar de verdad, usa:"
                f"\n    python manage.py generar_seguimientos_faltantes --aplicar"
                f"\n{'='*60}\n"
            ))
            return

        # 3. MODO REAL: Crear seguimientos + meses dentro de una transacción
        creados = 0
        meses_creados = 0

        with transaction.atomic():
            for venta in ventas_sin_seguimiento:
                fecha_inst = venta.fecha_real_inst
                if hasattr(fecha_inst, 'date'):
                    fecha_inst = fecha_inst.date()

                # Calcular las fechas proyectadas
                paquete = generar_fechas_proyectadas(fecha_real_instalacion=fecha_inst)

                # Crear la cabecera
                nuevo_seguimiento = Seguimiento.objects.create(
                    id_venta=venta,
                    ciclo_facturacion=paquete["ciclo_facturacion"],
                )

                # Crear los 6 meses
                registros_mensuales = []
                for mes_data in paquete["meses_detalle"]:
                    registros_mensuales.append(
                        SeguimientoMensual(
                            id_seguimiento=nuevo_seguimiento,
                            mes_numero=mes_data["mes_numero"],
                            fecha_seguimiento=mes_data["fecha_seguimiento"],
                            fecha_validacion_pago=mes_data["fecha_validacion_pago"],
                        )
                    )

                SeguimientoMensual.objects.bulk_create(registros_mensuales)

                creados += 1
                meses_creados += len(registros_mensuales)

        self.stdout.write(self.style.SUCCESS(
            f"\n{'='*60}"
            f"\n  ✅ MIGRACIÓN COMPLETADA EXITOSAMENTE"
            f"\n  → Seguimientos creados: {creados}"
            f"\n  → Registros mensuales creados: {meses_creados}"
            f"\n{'='*60}\n"
        ))
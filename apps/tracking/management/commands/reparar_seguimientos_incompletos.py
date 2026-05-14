"""
=========================================================================
SCRIPT DE MIGRACIÓN: Reparar Seguimientos Incompletos (Enero)
=========================================================================
Este comando busca los Seguimientos que ya existen (porque se crearon
en la importación de Excel para guardar el código de pago) pero que
están incompletos: NO tienen ciclo de facturación ni sus 6 meses.
=========================================================================
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.tracking.models import Seguimiento, SeguimientoMensual
from apps.tracking.utils_seguimiento import generar_fechas_proyectadas


class Command(BaseCommand):
    help = "Repara seguimientos que no tienen meses ni ciclo de facturación."

    def add_arguments(self, parser):
        parser.add_argument(
            '--aplicar',
            action='store_true',
            default=False,
            help='Con --aplicar, ejecuta los cambios.',
        )

    def handle(self, *args, **options):
        aplicar = options['aplicar']

        # Buscar seguimientos que NO tienen ciclo de facturación
        seguimientos_incompletos = Seguimiento.objects.filter(
            ciclo_facturacion__isnull=True,
            venta__fecha_real_inst__isnull=False
        ).select_related('venta')

        total = seguimientos_incompletos.count()

        if total == 0:
            self.stdout.write(self.style.SUCCESS(
                "\n✅ No hay seguimientos incompletos.\n"
            ))
            return

        self.stdout.write(self.style.WARNING(
            f"\n{'='*60}"
            f"\n  Se encontraron {total} seguimientos INCOMPLETOS (Ej. Enero)."
            f"\n{'='*60}\n"
        ))

        for i, seg in enumerate(seguimientos_incompletos, start=1):
            fecha_inst = seg.venta.fecha_real_inst
            if hasattr(fecha_inst, 'date'):
                fecha_inst = fecha_inst.date()

            paquete = generar_fechas_proyectadas(fecha_real_instalacion=fecha_inst)
            self.stdout.write(f"  {i:3d}. SOT: {seg.venta.codigo_sot} | Cód. Pago: {seg.codigo_pago} | Ciclo calculado: {paquete['ciclo_facturacion']}")

        if not aplicar:
            self.stdout.write(self.style.WARNING(
                "\n  MODO SIMULACIÓN. Para aplicar usa: python manage.py reparar_seguimientos_incompletos --aplicar\n"
            ))
            return

        creados = 0
        meses_creados = 0

        with transaction.atomic():
            for seg in seguimientos_incompletos:
                fecha_inst = seg.venta.fecha_real_inst
                if hasattr(fecha_inst, 'date'):
                    fecha_inst = fecha_inst.date()

                paquete = generar_fechas_proyectadas(fecha_real_instalacion=fecha_inst)

                # 1. Actualizar el seguimiento existente con el ciclo
                seg.ciclo_facturacion = paquete["ciclo_facturacion"]
                seg.save(update_fields=['ciclo_facturacion'])

                # 2. Crear los 6 meses
                registros_mensuales = []
                for mes_data in paquete["meses_detalle"]:
                    registros_mensuales.append(
                        SeguimientoMensual(
                            id_seguimiento=seg,
                            mes_numero=mes_data["mes_numero"],
                            fecha_seguimiento=mes_data["fecha_seguimiento"],
                            fecha_validacion_pago=mes_data["fecha_validacion_pago"],
                        )
                    )

                SeguimientoMensual.objects.bulk_create(registros_mensuales)
                creados += 1
                meses_creados += len(registros_mensuales)

        self.stdout.write(self.style.SUCCESS(
            f"\n✅ REPARACIÓN EXITOSA. Seguimientos actualizados: {creados} | Meses creados: {meses_creados}\n"
        ))
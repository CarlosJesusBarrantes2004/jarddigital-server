import csv
import os
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.ubigeo.models import Departamento, Provincia, Distrito


class Command(BaseCommand):
    help = "Carga ubigeo generando códigos jerárquicos (1 -> 101 -> 10101)"

    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=str)

    def handle(self, *args, **options):
        path = options["csv_file"]

        if not os.path.exists(path):
            self.stdout.write(self.style.ERROR(f"Archivo no encontrado: {path}"))
            return

        self.stdout.write("Limpiando tablas para carga limpia...")
        # Borramos en orden inverso para respetar las claves foráneas
        Distrito.objects.all().delete()
        Provincia.objects.all().delete()
        Departamento.objects.all().delete()

        # Contadores para generar los códigos de UBIGEO solicitados
        # Los IDs (Primary Keys) serán manejados automáticamente por la DB (autoincrement)

        # Cache para no consultar la DB repetidamente
        deps_cache = {}  # {'NOMBRE_DEP': objeto_dep}
        provs_cache = {}  # {'ID_DEP_Y_NOMBRE_PROV': objeto_prov}

        # Contadores lógicos para el código ubigeo
        dep_code_counter = 0

        with open(path, "r", encoding="utf-8") as f:
            # ¡OJO AQUÍ! Si tu archivo realmente usa comas, cambia delimiter=';' por delimiter=','
            reader = csv.reader(f, delimiter=";")

            try:
                with transaction.atomic():
                    for i, row in enumerate(reader, 1):
                        # Validación básica de estructura
                        if len(row) < 4:
                            continue

                        # Extracción según tu indicación:
                        # row[0] es el código original del CSV (lo ignoramos)
                        dep_nombre = row[1].strip().upper()  # 2da columna
                        prov_nombre = row[2].strip().upper()  # 3ra columna
                        dist_nombre = row[3].strip().upper()  # 4ta columna

                        if not dep_nombre or not prov_nombre or not dist_nombre:
                            continue

                        # -------------------------------------------------------
                        # 1. DEPARTAMENTO
                        # Lógica: Código inicia en 1, 2, 3...
                        # -------------------------------------------------------
                        if dep_nombre not in deps_cache:
                            dep_code_counter += 1
                            nuevo_dep = Departamento.objects.create(
                                nombre=dep_nombre,
                                codigo_ubigeo=str(dep_code_counter),  # Ej: "1", "2"
                            )
                            deps_cache[dep_nombre] = {
                                "obj": nuevo_dep,
                                "prov_code_counter": 0,  # Contador interno para sus provincias
                            }

                        current_dep_data = deps_cache[dep_nombre]
                        current_dep_obj = current_dep_data["obj"]

                        # -------------------------------------------------------
                        # 2. PROVINCIA
                        # Lógica: Código es {COD_DEP}{CORRELATIVO_2_DIGITOS}
                        # Ej: Si Dep es "1" y es la 1ra prov -> "101"
                        # -------------------------------------------------------
                        prov_key = (current_dep_obj.id, prov_nombre)

                        if prov_key not in provs_cache:
                            # Incrementamos el contador de provincias DENTRO de este departamento
                            current_dep_data["prov_code_counter"] += 1
                            num_prov = current_dep_data["prov_code_counter"]

                            # Formato: Dep "1" + Prov "01" = "101"
                            codigo_prov = (
                                f"{current_dep_obj.codigo_ubigeo}{num_prov:02d}"
                            )

                            nueva_prov = Provincia.objects.create(
                                nombre=prov_nombre,
                                codigo_ubigeo=codigo_prov,
                                id_departamento=current_dep_obj,
                            )
                            provs_cache[prov_key] = {
                                "obj": nueva_prov,
                                "dist_code_counter": 0,  # Contador interno para sus distritos
                            }

                        current_prov_data = provs_cache[prov_key]
                        current_prov_obj = current_prov_data["obj"]

                        # -------------------------------------------------------
                        # 3. DISTRITO
                        # Lógica: Código es {COD_PROV}{CORRELATIVO_2_DIGITOS}
                        # Ej: Si Prov es "101" y es el 1er dist -> "10101"
                        # -------------------------------------------------------
                        # Incrementamos contador de distritos DENTRO de esta provincia
                        current_prov_data["dist_code_counter"] += 1
                        num_dist = current_prov_data["dist_code_counter"]

                        # Formato: Prov "101" + Dist "01" = "10101"
                        codigo_dist = f"{current_prov_obj.codigo_ubigeo}{num_dist:02d}"

                        Distrito.objects.create(
                            nombre=dist_nombre,
                            codigo_ubigeo=codigo_dist,
                            id_provincia=current_prov_obj,
                        )

                self.stdout.write(
                    self.style.SUCCESS(f"¡Carga completada! Procesados {i} registros.")
                )

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error en fila {i}: {str(e)}"))

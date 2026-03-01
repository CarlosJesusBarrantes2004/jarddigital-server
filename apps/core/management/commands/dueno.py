from django.core.management.base import BaseCommand
from apps.users.models import Usuario, RolSistema


class Command(BaseCommand):
    help = "Crea o actualiza el usuario maestro con rol de DUEÑO"

    def handle(self, *args, **kwargs):
        # 1. Buscamos el Rol DUEÑO (debe haber sido creado por el script de catálogos)
        try:
            rol_dueno = RolSistema.objects.get(codigo="DUENO")
            self.stdout.write(
                self.style.SUCCESS(f" foundry: Rol '{rol_dueno.nombre}' encontrado.")
            )
        except RolSistema.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    "❌ Error: El rol 'DUENO' no existe en la base de datos.\n"
                    "TIP: Ejecuta primero el script de población de catálogos."
                )
            )
            return

        # 2. Intentamos obtener al usuario o prepararlo para creación
        # Usamos update_or_create para que si ya existe, simplemente le asigne el rol correcto
        admin_username = "admin"

        user, created = Usuario.objects.get_or_create(
            username=admin_username,
            defaults={
                "email": "admin@jarddigital.com",
                "nombre_completo": "Renato Manay",
                "id_rol": rol_dueno,
                "is_staff": True,
                "is_superuser": True,
                "activo": True,
            },
        )

        if created:
            # Si el usuario es nuevo, establecemos su contraseña
            user.set_password("pass123456")
            user.save()
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ ¡Usuario maestro '{admin_username}' creado con éxito!"
                )
            )
        else:
            # Si el usuario ya existía, actualizamos el rol por si acaso
            user.id_rol = rol_dueno
            # Opcional: podrías actualizar nombre_completo o email aquí también
            user.save()
            self.stdout.write(
                self.style.WARNING(
                    f"⚠️ El usuario '{admin_username}' ya existía. Se ha verificado su rol de DUEÑO."
                )
            )

        self.stdout.write(self.style.SUCCESS("🚀 Proceso finalizado correctamente."))

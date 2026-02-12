from rest_framework import serializers
from .models import Usuario, RolSistema

# 1. Serializador para el Rol (para que no salga solo el ID)
class RolSistemaSerializer(serializers.ModelSerializer):
    class Meta:
        model = RolSistema
        fields = ['id', 'codigo', 'nombre', 'nivel_jerarquia']

# 2. Serializador del Usuario
class UsuarioSerializer(serializers.ModelSerializer):
    # Aquí incrustamos el serializador del rol para ver el detalle completo
    rol = RolSistemaSerializer(source='id_rol', read_only=True)

    class Meta:
        model = Usuario
        # Estos son los campos que verá tu compañero en el frontend
        fields = [
            'id',
            'username',
            'nombre_completo',
            'email',
            'rol',
            'activo'
        ]

# 2. Serializador para Registro de Usuarios

class UserRegisterSerializer(serializers.ModelSerializer):
    # 1. Definimos la contraseña como "write_only" para que nadie pueda leerla después de crearla
    password = serializers.CharField(write_only=True)

    class Meta:
        model = Usuario
        # 2. Estos son los campos que Postman debe enviar
        fields = [
            'username',
            'password',
            'nombre_completo',
            'email',
            'id_rol',  # Django espera el ID (ej: 1, 2)
            'activo'
        ]

    def create(self, validated_data):
        # 3. Separamos la contraseña del resto de datos
        password = validated_data.pop('password')

        # 4. Usamos la función mágica create_user que ENCRIPTA la clave
        user = Usuario.objects.create_user(
            password=password,
            **validated_data  # Pasa el resto (username, nombre, rol, etc.)
        )
        return user
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .serializers import UsuarioSerializer
from rest_framework import generics
from rest_framework.permissions import IsAdminUser
from .serializers import UserRegisterSerializer

class UserMeView(APIView):
    """
    Devuelve los datos del usuario logueado basándose en su Token.
    """
    permission_classes = [IsAuthenticated] # ¡Solo usuarios con Token entran aquí!

    def get(self, request):
        # El usuario ya viene en 'request.user' gracias al Token
        serializer = UsuarioSerializer(request.user)
        return Response(serializer.data)


class UserRegisterView(generics.CreateAPIView):
    """
    Endpoint para crear nuevos usuarios (Vendedores, Supervisores, etc.)
    Solo accesible por administradores.
    """
    # Usamos el serializador que acabamos de crear
    serializer_class = UserRegisterSerializer
    # ¡Candado! Solo admins pueden entrar aquí
    permission_classes = [IsAdminUser]
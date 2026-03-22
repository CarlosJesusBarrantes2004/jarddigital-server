from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, filters
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from .serializers import UsuarioSerializer, UsuarioAdminSerializer, RolSistemaSerializer, SupervisorAsignacionSerializer
from .permissions import PuedeGestionarUsuarios, SoloLecturaRolesOCrearDueno
from .models import Usuario, RolSistema, SupervisorAsignacion
from .selectors import obtener_usuarios_permitidos
from apps.core.mixins import SoftDeleteModelViewSet
from django.conf import settings
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework_simplejwt.views import TokenObtainPairView
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response


class CustomTokenObtainPairView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            access_token = response.data.get("access")

            response.set_cookie(
                key=settings.AUTH_COOKIE,
                value=access_token,
                httponly=settings.AUTH_COOKIE_HTTP_ONLY,
                secure=settings.AUTH_COOKIE_SECURE,
                samesite=settings.AUTH_COOKIE_SAMESITE,
                path="/",
            )

            del response.data["access"]
            if "refresh" in response.data:
                del response.data["refresh"]

        return response

class RolSistemaViewSet(SoftDeleteModelViewSet):
    """CRUD de los roles del sistema (Dueño, Supervisor, Asesor)"""
    queryset = RolSistema.objects.all()
    serializer_class = RolSistemaSerializer
    permission_classes = [IsAuthenticated, SoloLecturaRolesOCrearDueno]

class UserMeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=UsuarioSerializer)
    def get(self, request):
        serializer = UsuarioSerializer(request.user)
        return Response(serializer.data)


# En 4 líneas obtenemos GET, POST, PUT, PATCH y DELETE lógico.
class UsuarioViewSet(SoftDeleteModelViewSet):
    # Base del queryset: Optimizamos las consultas para traer toda la info relacionada de una sola vez
    queryset = Usuario.objects.select_related('id_rol').prefetch_related(
        'permisos__id_modalidad_sede__id_sucursal',
        'permisos__id_modalidad_sede__id_modalidad'
    ).all()

    serializer_class = UsuarioAdminSerializer
    permission_classes = [IsAuthenticated, PuedeGestionarUsuarios]

    # Activamos búsqueda y filtros
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]

    # ---> FIX #7: Mantenemos 'activo' para que DjangoFilterBackend funcione <---
    filterset_fields = ['id_rol', 'activo']

    search_fields = ['nombre_completo', 'username', 'email']

    def get_queryset(self):
        queryset = super().get_queryset()

        # 1. Aplicamos Seguridad de Filas usando el Selector
        queryset = obtener_usuarios_permitidos(self.request.user, queryset)

        # 2. Filtro Dinámico del Frontend
        filtro_sede_id = self.request.query_params.get("id_modalidad_sede")
        if filtro_sede_id:
            queryset = queryset.filter(permisos__id_modalidad_sede=filtro_sede_id).distinct()

        return queryset


class SupervisorAsignacionViewSet(SoftDeleteModelViewSet):
    # Optimización Extrema: Traemos toda la cadena de nombres en un solo JOIN de SQL
    queryset = SupervisorAsignacion.objects.select_related(
        'id_supervisor',
        'id_modalidad_sede__id_sucursal',
        'id_modalidad_sede__id_modalidad'
    ).all().order_by('-fecha_inicio')

    serializer_class = SupervisorAsignacionSerializer
    # Usamos el permiso de jefatura que ya tenías para que un asesor no se asigne a sí mismo como jefe
    permission_classes = [IsAuthenticated, PuedeGestionarUsuarios]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter]

    # Filtros para que RRHH pueda buscar: "?id_supervisor=3" o "?activo=True"
    filterset_fields = ['id_supervisor', 'id_modalidad_sede', 'activo']

    # Buscador de texto libre para nombres de supervisor o sucursales
    search_fields = [
        'id_supervisor__nombre_completo',
        'id_modalidad_sede__id_sucursal__nombre'
    ]


class LogoutView(APIView):
    # Protegemos el logout para que no explote si entra alguien sin sesión
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Cerrar Sesión",
        description="Elimina la cookie de autenticación (JWT) del navegador del usuario.",
        request=None,  # Le decimos que no necesitamos que envíen ningún JSON en el body
        responses={
            200: inline_serializer(
                name='LogoutResponse',
                fields={
                    'detail': serializers.CharField(default='Sesión cerrada correctamente')
                }
            )
        }
    )
    def post(self, request):
        response = Response({"detail": "Sesión cerrada correctamente"}, status=200)

        response.delete_cookie(
            settings.AUTH_COOKIE, path="/", samesite=settings.AUTH_COOKIE_SAMESITE
        )

        return response

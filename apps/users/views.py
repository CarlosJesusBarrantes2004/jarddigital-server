from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, filters
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from .serializers import (
    UsuarioSerializer,
    UsuarioAdminSerializer,
    RolSistemaSerializer,
    SupervisorAsignacionSerializer,
)
from .permissions import PuedeGestionarUsuarios, SoloLecturaRolesOCrearDueno
from .models import Usuario, RolSistema, SupervisorAsignacion
from apps.core.mixins import SoftDeleteModelViewSet
from django.conf import settings
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework_simplejwt.views import TokenObtainPairView
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status


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
    queryset = (
        Usuario.objects.select_related("id_rol")
        .prefetch_related(
            "permisos__id_modalidad_sede__id_sucursal",
            "permisos__id_modalidad_sede__id_modalidad",
        )
        .all()
    )

    serializer_class = UsuarioAdminSerializer
    permission_classes = [IsAuthenticated, PuedeGestionarUsuarios]

    # Activamos búsqueda y filtros
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["id_rol", "activo"]
    search_fields = ["nombre_completo", "username", "email"]

    def get_queryset(self):
        """
        Sobreescribimos la consulta base para aplicar filtros de seguridad
        y filtros dinámicos del frontend.
        """
        user = self.request.user

        activo_param = self.request.query_params.get("activo")

        queryset = (
            Usuario.objects.select_related("id_rol")
            .prefetch_related(
                "permisos__id_modalidad_sede__id_sucursal",
                "permisos__id_modalidad_sede__id_modalidad",
            )
            .all()
        )

        if activo_param is None:
            queryset = queryset.filter(activo=True)

        # ==========================================
        # FASE 1: SEGURIDAD (Row-Level Security)
        # ==========================================
        if hasattr(user, "id_rol") and user.id_rol:

            # Si es SUPERVISOR, creamos su "universo cerrado" de datos
            if user.id_rol.codigo == "SUPERVISOR":
                sedes_supervisor_ids = user.asignaciones_supervisor.filter(
                    activo=True, fecha_fin__isnull=True
                ).values_list("id_modalidad_sede", flat=True)

                queryset = queryset.filter(
                    id_rol__codigo="ASESOR",
                    # ¡CORREGIDO: Los dobles guiones bajos son obligatorios!
                    permisos__id_modalidad_sede__in=sedes_supervisor_ids,
                ).distinct()

        # ==========================================
        # FASE 2: FILTRO DINÁMICO DEL FRONTEND
        # ==========================================
        # Leemos el parámetro de la URL (ej: /usuarios/?id_modalidad_sede=3)
        filtro_sede_id = self.request.query_params.get("id_modalidad_sede")

        if filtro_sede_id:
            # Filtramos el universo de usuarios para mostrar solo los de esa sede
            queryset = queryset.filter(
                permisos__id_modalidad_sede=filtro_sede_id
            ).distinct()

        return queryset

    @action(detail=True, methods=["patch"], url_path="reactivar")
    def reactivar(self, request, pk=None):
        """
        PATCH /api/users/empleados/{id}/reactivar/
        Reactiva un usuario que fue desactivado.
        Busca en TODOS los usuarios (no solo activos).
        """
        try:
            usuario = Usuario.objects.get(pk=pk)
        except Usuario.DoesNotExist:
            return Response(
                {"detail": "Usuario no encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        usuario.activo = True
        usuario.save(update_fields=["activo"])

        # El signal gestionar_grabador_automatico se dispara automáticamente aquí
        # y reactiva el GrabadorAudio asociado al usuario. Sin código extra.

        serializer = self.get_serializer(usuario)
        return Response(serializer.data)


class SupervisorAsignacionViewSet(SoftDeleteModelViewSet):
    # Optimización Extrema: Traemos toda la cadena de nombres en un solo JOIN de SQL
    queryset = (
        SupervisorAsignacion.objects.select_related(
            "id_supervisor",
            "id_modalidad_sede__id_sucursal",
            "id_modalidad_sede__id_modalidad",
        )
        .all()
        .order_by("-fecha_inicio")
    )

    serializer_class = SupervisorAsignacionSerializer
    # Usamos el permiso de jefatura que ya tenías para que un asesor no se asigne a sí mismo como jefe
    permission_classes = [IsAuthenticated, PuedeGestionarUsuarios]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter]

    # Filtros para que RRHH pueda buscar: "?id_supervisor=3" o "?activo=True"
    filterset_fields = ["id_supervisor", "id_modalidad_sede", "activo"]

    # Buscador de texto libre para nombres de supervisor o sucursales
    search_fields = [
        "id_supervisor__nombre_completo",
        "id_modalidad_sede__id_sucursal__nombre",
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
                name="LogoutResponse",
                fields={
                    "detail": serializers.CharField(
                        default="Sesión cerrada correctamente"
                    )
                },
            )
        },
    )
    def post(self, request):
        response = Response({"detail": "Sesión cerrada correctamente"}, status=200)

        response.delete_cookie(
            settings.AUTH_COOKIE, path="/", samesite=settings.AUTH_COOKIE_SAMESITE
        )

        return response

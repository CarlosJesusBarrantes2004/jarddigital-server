from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserMeView, UsuarioViewSet, LogoutView, RolSistemaViewSet, SupervisorAsignacionViewSet

router = DefaultRouter()
# Esto crea automáticamente /api/users/empleados/ y /api/users/empleados/<id>/
router.register(r'empleados', UsuarioViewSet, basename='empleados')
router.register(r'roles', RolSistemaViewSet, basename='roles')
router.register(r'asignaciones-supervisor', SupervisorAsignacionViewSet, basename='asignacion-supervisor')

urlpatterns = [
    path("me/", UserMeView.as_view(), name="user-me"),
    path("logout/", LogoutView.as_view(), name="user-logout"),
    # Incluimos las rutas del CRUD
    path('', include(router.urls)),
]

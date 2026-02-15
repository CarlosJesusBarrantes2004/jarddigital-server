from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserMeView, UsuarioViewSet, LogoutView

router = DefaultRouter()
# Esto crea automáticamente /api/users/gestion/ y /api/users/gestion/<id>/
router.register(r'gestion', UsuarioViewSet, basename='gestion-usuarios')

urlpatterns = [
    path("me/", UserMeView.as_view(), name="user-me"),
    path("logout/", LogoutView.as_view(), name="user-logout"),
    # Incluimos las rutas del CRUD
    path('', include(router.urls)),
]

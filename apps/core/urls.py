from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SucursalViewSet, ModalidadViewSet

# El Router crea automáticamente todas las rutas CRUD
router = DefaultRouter()
router.register(r'sucursales', SucursalViewSet, basename='sucursal')
router.register(r'modalidades', ModalidadViewSet, basename='modalidad')

urlpatterns = [
    path('', include(router.urls)),
]
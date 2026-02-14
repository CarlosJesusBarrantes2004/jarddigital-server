from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SucursalViewSet, ModalidadViewSet, TipoDocumentoViewSet, ModalidadSedeOpcionesViewSet

# El Router crea automáticamente todas las rutas CRUD
router = DefaultRouter()
router.register(r'sucursales', SucursalViewSet, basename='sucursal')
router.register(r'modalidades', ModalidadViewSet, basename='modalidad')
router.register(r'tipos-documento', TipoDocumentoViewSet, basename='tipo-documento')
router.register(r'opciones-sedes', ModalidadSedeOpcionesViewSet, basename='opciones-sedes')

urlpatterns = [
    path('', include(router.urls)),
]
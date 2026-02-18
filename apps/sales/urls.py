from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Importamos las vistas que acabamos de crear
from .views import (
    EstadoSOTViewSet,
    SubEstadoSOTViewSet,
    EstadoAudioViewSet,
    ProductoViewSet,
    GrabadorAudioViewSet,
    VentaViewSet
)

# Instanciamos el enrutador automático
router = DefaultRouter()

# Registramos nuestros 5 catálogos
router.register(r'estados-sot', EstadoSOTViewSet, basename='estado-sot')
router.register(r'sub-estados-sot', SubEstadoSOTViewSet, basename='sub-estado-sot')
router.register(r'estados-audio', EstadoAudioViewSet, basename='estado-audio')
router.register(r'productos', ProductoViewSet, basename='producto')
router.register(r'grabadores', GrabadorAudioViewSet, basename='grabador-audio')

# Registramos el endpoint transaccional principal
router.register(r'ventas', VentaViewSet, basename='venta') # <--- ¡EL ENCHUFE FINAL!

urlpatterns = [
    # Le decimos a Django que incluya todas las URLs generadas por el router
    path('', include(router.urls)),
]

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductoViewSet

# 1. Instanciamos el enrutador mágico de DRF
router = DefaultRouter()

# 2. Registramos nuestro ViewSet. DRF creará automáticamente todas las rutas
# Base url: /api/sales/productos/
router.register(r'productos', ProductoViewSet, basename='producto')

# 3. Incluimos las rutas generadas en los urlpatterns
urlpatterns = [
    path('', include(router.urls)),
]

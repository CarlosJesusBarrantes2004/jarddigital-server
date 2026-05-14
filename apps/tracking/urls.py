from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SeguimientoViewSet, SeguimientoMensualViewSet

# Instanciamos el enrutador automático
router = DefaultRouter()

# Registramos nuestros endpoints transaccionales
router.register(r'seguimientos', SeguimientoViewSet, basename='seguimientos')
router.register(r'seguimientos-mensuales', SeguimientoMensualViewSet, basename='seguimientos-mensuales')

urlpatterns = [
    # Le decimos a Django que incluya todas las URLs generadas por el router
    path('', include(router.urls)),
]
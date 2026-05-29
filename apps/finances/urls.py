from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AsistenciaViewSet

# Inicializamos el enrutador principal de Finanzas
router = DefaultRouter()

router.register(r'asistencias', AsistenciaViewSet, basename='asistencia')

urlpatterns = [
    # Incluimos todas las rutas generadas por el router
    path('', include(router.urls)),
]
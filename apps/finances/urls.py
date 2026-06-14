from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AsistenciaViewSet, ReglaComisionViewSet, LiquidacionRRHHViewSet, MiDashboardFinancieroView

# Inicializamos el enrutador principal de Finanzas
router = DefaultRouter()

router.register(r'asistencias', AsistenciaViewSet, basename='asistencia')

# Rutas del Dueño: /api/finances/reglas-comision/
router.register(r'reglas-comision', ReglaComisionViewSet, basename='regla-comision')

# Rutas de RRHH: /api/finances/planillas/ y /api/finances/planillas/ejecutar_liquidacion/
router.register(r'planillas', LiquidacionRRHHViewSet, basename='planilla')

urlpatterns = [
    # Incluimos todas las rutas generadas por el router
    path('', include(router.urls)),

    # Ruta del Asesor: /api/finances/mi-dashboard/?mes=6&anio=2026
    path('mi-dashboard/', MiDashboardFinancieroView.as_view(), name='mi-dashboard'),
]
from rest_framework.routers import DefaultRouter
from .views import SeguimientoViewSet, SeguimientoMensualViewSet

router = DefaultRouter()
router.register(r'seguimientos', SeguimientoViewSet, basename='seguimientos')
router.register(r'seguimientos-mensuales', SeguimientoMensualViewSet, basename='seguimientos-mensuales')

urlpatterns = router.urls
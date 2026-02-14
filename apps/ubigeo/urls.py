from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DepartamentoViewSet, ProvinciaViewSet, DistritoViewSet

router = DefaultRouter()
router.register(r'departamentos', DepartamentoViewSet, basename='departamento')
router.register(r'provincias', ProvinciaViewSet, basename='provincia')
router.register(r'distritos', DistritoViewSet, basename='distrito')

urlpatterns = [
    path('', include(router.urls)),
]
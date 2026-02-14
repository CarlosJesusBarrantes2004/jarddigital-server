from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from apps.core.mixins import SoftDeleteModelViewSet
from .models import Producto
from .serializers import ProductoSerializer

# Cambiamos ListView por nuestro ViewSet personalizado
class ProductoViewSet(SoftDeleteModelViewSet):
    # Pasamos a .all() porque el mixin ya se encarga de filtrar los inactivos
    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer
    permission_classes = [IsAuthenticated]

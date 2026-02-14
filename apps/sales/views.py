from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import Producto
from .serializers import ProductoSerializer

class ProductoListView(generics.ListAPIView):
    queryset = Producto.objects.filter(activo=True) # Solo productos activos
    serializer_class = ProductoSerializer
    permission_classes = [IsAuthenticated]

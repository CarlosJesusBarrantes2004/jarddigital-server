from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import Producto, TipoDocumento
from .serializers import ProductoSerializer, TipoDocumentoSerializer

class ProductoListView(generics.ListAPIView):
    queryset = Producto.objects.filter(activo=True) # Solo productos activos
    serializer_class = ProductoSerializer
    permission_classes = [IsAuthenticated]

class TipoDocumentoListView(generics.ListAPIView):
    queryset = TipoDocumento.objects.filter(activo=True)
    serializer_class = TipoDocumentoSerializer
    permission_classes = [IsAuthenticated]
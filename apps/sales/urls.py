from django.urls import path
from .views import ProductoListView, TipoDocumentoListView

urlpatterns = [
    path('productos/', ProductoListView.as_view(), name='lista-productos'),
    path('documentos/', TipoDocumentoListView.as_view(), name='lista-documentos'),
]
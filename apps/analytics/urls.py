# apps/analytics/urls.py

from django.urls import path
from .views import (
    MatrizRendimientoView,
    BarrasRendimientoView,
    TendenciaDiariaView,
    DistribucionJerarquicaView
)

urlpatterns = [
    # Gráficos 1 y 3 (Matriz Pivote)
    path('matriz-rendimiento/', MatrizRendimientoView.as_view(), name='analytics-matriz'),

    # Gráficos 2 y 4 (Barras)
    path('barras-rendimiento/', BarrasRendimientoView.as_view(), name='analytics-barras'),

    # Gráfico 5 (Líneas comparativas)
    path('tendencia-diaria/', TendenciaDiariaView.as_view(), name='analytics-tendencia'),

    # Gráfico 6 (Árbol Jerárquico Drill-Down)
    path('distribucion-jerarquica/', DistribucionJerarquicaView.as_view(), name='analytics-jerarquia'),
]